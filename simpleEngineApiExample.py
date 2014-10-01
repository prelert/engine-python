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
Creates a new job and uploads farequote.csv to it. The job is
then closed and the result buckets queried,

The example file used can be downloaded from 
http://s3.amazonaws.com/prelert_demo/farequote.csv and looks like this:

    time,airline,responsetime,sourcetype
    2014-06-23 00:00:00Z,AAL,132.2046,farequote
    2014-06-23 00:00:00Z,JZA,990.4628,farequote
    2014-06-23 00:00:00Z,JBU,877.5927,farequote

The script is invoked with 1 positional argument the farequote.csv 
file and has optional arguments to specify the location of the 
Engine API. Run the script with '--help' to see the options.

The output is CSV print out of date, bucket id and anomaly score.
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
BASE_URL = 'engine/v1'


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
    parser.add_argument("file", help="Path to farequote.csv")

    return parser.parse_args()   


def main():

    setupLogging()

    args = parseArguments()

    # Create the REST API client
    engine_client = EngineApiClient(args.host, BASE_URL, args.port)

    job_config = '{"analysisConfig" : {\
                        "bucketSpan":3600,\
                        "detectors" :[{"function":"metric","fieldName":"responsetime","byFieldName":"airline"}] },\
                        "dataDescription" : {"fieldDelimiter":",", "timeField":"time", "timeFormat":"yyyy-MM-dd HH:mm:ssX"} }'

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
        print "Date,Anomaly Score,Max Normalized Probablility"
        for bucket in response:                                
            print "{0},{1},{2}".format(bucket['timestamp'], bucket['anomalyScore'], 
                        bucket['maxNormalizedProbability'])


if __name__ == "__main__":
    main()    

