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
Pull the latest results for the provided job id and print
the bucket timestamp, bucket id and anomaly score.

The script is invoked with 1 positional argument -the id of the 
job to query the results of. Additional optional arguments
to specify the location of the Engine API. Run the script with 
'--help' to see the options.

If the --continue-poll flag is set then loop 
indefinitley polling every 10 seconds for any new results. 
'''

import argparse
import sys
import json
import logging
import time

from prelert.engineApiClient import EngineApiClient

# defaults
HOST = 'localhost'
PORT = 8080
BASE_URL = 'engine/v1'

# time between polling for new results
POLL_INTERVAL_SECS = 10


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
    parser.add_argument("--continue-poll", action='store_true', help="If set then "
        "continue polling in real time for new results", dest="continue_poll")
    parser.add_argument("--anomalyScore", help="Filter out buckets with an anomalyScore "  
        + "less than this", type=float, default=0.0)
    parser.add_argument("--normalizedProbability", help="Filter out buckets with an " 
        + "max normalized probablilty less than this", type=float, default=0.0)    
    parser.add_argument("jobid", help="The jobId to request results from", default="0")
    return parser.parse_args()   


def printHeader():
    print "Date,Anomaly Score,Max Normalized Probablility"

def printBuckets(buckets):
    for bucket in buckets:
        print "{0},{1},{2}".format(bucket['timestamp'], bucket['anomalyScore'], 
            bucket['maxNormalizedProbability'])

def main():

    setupLogging()

    args = parseArguments()
    job_id = args.jobid

    # Create the REST API client
    engine_client = EngineApiClient(args.host, BASE_URL, args.port)

    # Get all the buckets up to now
    logging.info("Get result buckets for job " + job_id)
    (http_status_code, response) = engine_client.getAllBuckets(job_id, 
        include_records=False, 
        anomaly_score_filter_value=args.anomalyScore,
        normalized_probability_filter_value=args.normalizedProbability)

    
    if http_status_code != 200:
        print (http_status_code, json.dumps(response))
        return
    
    
    printHeader()
    printBuckets(response)

    if args.continue_poll:

        if len(response) > 0:
            next_bucket_id = int(response[-1]['id']) + 1
        else:
            next_bucket_id = None
        
        while True:
            # Wait POLL_INTERVAL_SECS then query for any new buckets
            time.sleep(POLL_INTERVAL_SECS)

            (http_status_code, response) = engine_client.getBucketsByDate(job_id=job_id, 
                start_date=str(next_bucket_id), end_date=None, 
                include_records=False,         
                anomaly_score_filter_value=args.anomalyScore,
                normalized_probability_filter_value=args.normalizedProbability)

            if http_status_code != 200:
                print (http_status_code, json.dumps(response))
                break

            printBuckets(response)
            
            if len(response) > 0:
                next_bucket_id = int(response[-1]['id']) + 1


if __name__ == "__main__":
    main()    

