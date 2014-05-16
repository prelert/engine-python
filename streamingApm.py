#!/usr/bin/env python
############################################################################
#                                                                          #
# Copyright 2014 Prelert Ltd                                               #
#                                                                          #
# Licensed under the Apache License, Version 2.0 (the "License");          #
# you may not use this file except in compliance with the License.         #
# You may obtain a copy of the License at                                  #
#                                                                          #
#    http://www.apache.org/licenses/LICENSE-2.0                            #
#                                                                          #
# Unless required by applicable law or agreed to in writing, software      #
# distributed under the License is distributed on an "AS IS" BASIS,        #
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. #
# See the License for the specific language governing permissions and      #
# limitations under the License.                                           #
#                                                                          #
############################################################################
'''
    

    Use Ctrl-C to stop this script - the interrupt is caught and 
    the job closed gracefully
'''

import argparse
import csv
import json
import logging
import sys
import time
from datetime import datetime
from datetime import timedelta

from engineApiClient import EngineApiClient

# Default connection prarams
HOST = 'localhost'
PORT = 8080
BASE_URL = 'engine/v0.3'



def parseArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", help="The Prelert Engine API host, defaults to "
        + HOST, default=HOST)    
    parser.add_argument("--port", help="The Prelert Engine API port, defaults to " 
        + str(PORT), default=PORT)
    parser.add_argument("--duration", help="The number of hours to generate \
        data for. If not set script will produce records from the historical \
        start date until the time now", default=0)
    parser.add_argument("file", help="Path to APM data")

    return parser.parse_args()   


def generateRecords(csv_filename, start_date, interval, end_date):
    '''
    Generator function reads csv data file and returns records
    with an updated timestamp on demand.

    Records are read from a file and stored in a local array, once
    all the records have been read the function does not loop 
    round to the beginning again instead it flips and outputs
    the records in reverse order and so on.

    The csv file must contain a field with the name 'time'
    '''

    csv_data = []
    csv_file = open(csv_filename, 'rb')
    reader = csv.reader(csv_file)
    header = reader.next()
            
    time_field_idx = -1
    for i in range(len(header)):
        if header[i] == 'time':
            time_field_idx = i
            break    

    if time_field_idx == -1:
        logging.error("Cannot find 'time' field in csv header")
        return 

    reverse = False
    while start_date < end_date:          
        try:
            yield header
           
            if len(csv_data) == 0:
                # populate csv_data record
                for row in reader:
                    row[time_field_idx] = start_date.isoformat()
                    start_date += interval

                    csv_data.append(row)

                    yield row

                    if start_date > end_date:
                        break

                csv_file.close()
            else:
                if reverse:
                    for row in reversed(csv_data):
                        row[time_field_idx] = start_date.isoformat()
                        start_date += interval
                        yield row

                        if start_date > end_date:
                            break
                else:
                    for row in csv_data:
                        row[time_field_idx] = start_date.isoformat()
                        start_date += interval
                        yield row

                        if start_date > end_date:
                            break                

            reverse = not reverse

        except KeyboardInterrupt:
            raise StopIteration    



def main():
    args = parseArguments()

    start_date = datetime(2011, 05, 15, 0, 0, 0)    
    # interval between the generated timestamps for the records
    interval = timedelta(seconds=300)


    if args.duration <= 0:
        end_date = datetime.now()
    else:
        duration = timedelta(hours=args.duration)
        end_date = start_date + duration



    job_config = '{"analysisConfig" : {\
            "bucketSpan":3600,\
            "detectors" :[\
                {"fieldName":"In Discards","byFieldName":"host"},\
                {"fieldName":"In Octets","byFieldName":"host"},\
                {"fieldName":"Out Discards","byFieldName":"host"},\
                {"fieldName":"Out Octets","byFieldName":"host"} \
            ]\
        },\
        "dataDescription" : {\
            "fieldDelimiter":",",\
            "timeField":"time",\
            "timeFormat":"yyyy-MM-dd\'T\'HH:mm:ss"\
        }\
    }'
    

    engine_client = EngineApiClient.EngineApiClient(args.host, BASE_URL, args.port)
    (http_status_code, response) = engine_client.createJob(job_config)
    if http_status_code != 201:        
        print (http_status_code, json.dumps(response))
        return

    job_id = response['id']
    print 'Job created with Id = ' + job_id

    # get the csv header (the first record generated)
    record_generator = generateRecords(args.file, start_date, interval, end_date)    
    header = ','.join(next(record_generator))
    header += '\n'


    count = 0
    data = header
    try:
        for record in record_generator:
            # format as csv and append new line
            csv = ','.join(record) + '\n'
            data += csv 
            # print data

            count += 1
            if count == 100:            
                (http_status_code, response) = engine_client.upload(job_id, data)
                if http_status_code != 202:                    
                    print (http_status_code, json.dumps(response))
                    break                    

                # commit the uploaded data
                engine_client.close(job_id)

                # must send the header every time    
                data = header
                count = 0

            time.sleep(0.1)

    except KeyboardInterrupt:
        print "Keyboard interrupt closing job..."
                
    engine_client.close(job_id)


if __name__ == "__main__":
    main()    

