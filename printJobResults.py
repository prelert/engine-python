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
Pull the latest results for the provided job id then loop 
indefinitley polling 1 per second for any new results.
Prints the bucket timestamp, bucket id and anomaly score.

The script is invoked with 1 positional argument -the id of the 
job to query the results of. Additional optional arguments
to specify the location of the Engine API. Run the script with 
'--help' to see the options.

Use Ctrl-C to stop this script
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
BASE_URL = 'engine/v0.3'

# time between polling for new results
POLL_INTERVAL_SECS = 1.0


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
    parser.add_argument("jobid", help="The jobId to request results from", default="0")
    return parser.parse_args()   


def main():

    setupLogging()

    args = parseArguments()
    host = args.host
    port = args.port
    base_url = BASE_URL
    job_id = args.jobid

    # Create the REST API client
    engine_client = EngineApiClient(host, base_url, port)

    # Get all the buckets up to now
    logging.info("Get result buckets for job " + job_id)
    (http_status_code, response) = engine_client.getAllBuckets(job_id)
    if http_status_code != 200:
        print (http_status_code, json.dumps(response))
        return
    
    
    print "Date,BucketId,AnomalyScore"
    for bucket in response:
        print "{0},{1},{2}".format(bucket['timestamp'], bucket['id'], bucket['anomalyScore'])
    
    if len(response) > 0:
        next_bucket_id = int(response[-1]['id']) + 1
    else:
        next_bucket_id = None

    # Wait POLL_INTERVAL_SECS then query for any new buckets
    while True:
        time.sleep(POLL_INTERVAL_SECS)

        (http_status_code, response) = engine_client.getBucketsByDate(job_id=job_id, 
            start_date=str(next_bucket_id), end_date=None)
        if http_status_code != 200:
            print (http_status_code, json.dumps(response))
            break

        for bucket in response:
            print "{0},{1},{2}".format(bucket['timestamp'], bucket['id'], bucket['anomalyScore'])
        
        if len(response) > 0:
            next_bucket_id = int(response[-1]['id']) + 1


if __name__ == "__main__":
    main()    

