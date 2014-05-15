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
    Creates a new job and uploads flightcentre.csv to it. The job is
    then closed and the result buckets queried

    The output is csv format of date, bucket id and anomaly score
        airline,responsetime,time
        DJA,622,2012-10-21T13:00:00+0000
        JQA,1742,2012-10-21T13:00:01+0000
        GAL,5339,2012-10-21T13:00:02+0000

    If a bucket id is specified only the anomaly records for that bucket
    are returned.
'''

import argparse
import sys
import json
import logging


from prelert.engineApiClient import EngineApiClient


# Prelert Engine API connection prarams
HOST = 'localhost'
PORT = 8080
BASE_URL = 'engine/v0.3'


def setupLogging():
    '''
        Log to console
    '''    
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')

def parseArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", help="The Prelert Engine API host, defaults to "
        + HOST, default=HOST)    
    parser.add_argument("--port", help="The Prelert Engine API port, defaults to " 
        + str(PORT), default=PORT)
    parser.add_argument("file", help="Path to flightcentre.csv")

    return parser.parse_args()   


def main():

    setupLogging()

    args = parseArguments()

    # Create the REST API client
    engine_client = EngineApiClient(args.host, BASE_URL, args.port)

    job_config = '{"analysisConfig" : {\
                        "bucketSpan":3600,\
                        "detectors" :[{"fieldName":"responsetime","byFieldName":"airline"}] },\
                        "dataDescription" : {"fieldDelimiter":",", "timeField":"time", "timeFormat":"yyyy-MM-dd\'T\'HH:mm:ssX"} }'

    logging.info("Creating job")
    (http_status_code, response) = engine_client.createJob(job_config)
    if http_status_code != 201:
        print (http_status_code, json.dumps(response))
        return

    job_id = response['id']

    logging.info("Uploading data to " + job_id)
    file = open(args.file, 'rb')
    (http_status_code, response) = engine_client.upload(job_id, file)
    if http_status_code != 202:
        print (http_status_code, json.dumps(response))
        return


    logging.info("Closing job " + job_id)
    (http_status_code, response) = engine_client.close(job_id)
    if http_status_code != 202:
        print (http_status_code, json.dumps(response))
        return

    logging.info("Get result buckets for job " + job_id)
    (http_status_code, response) = engine_client.getAllBuckets(job_id)
    if http_status_code != 200:
        print (http_status_code, json.dumps(response))
    else:
        print "Date,AnomalyScore"
        for bucket in response:                                
            print "{0},{1}".format(bucket['timestamp'], bucket['anomalyScore']) 


if __name__ == "__main__":
    main()    

