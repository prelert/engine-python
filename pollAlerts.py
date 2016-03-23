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
Subscribe to the Prelert Engine API Alerts long poll end point for
alerts.

The script is invoked with 1 positional argument -the id of the
job to alert on. Optional parameters set the threshold arguments
at which to alert on. One of --anomalyScore or --normalizedProbability
should be set.

The script runs in an infinite loop re-subscribing to new alerts after
the request either times out or an alert is returned.

Run the script with '--help' to see the options.

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
BASE_URL = 'engine/v2'


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
    parser.add_argument("--anomalyScore", help="Alert on buckets with anomaly score >= "
        + "this value", type=float, default=None)
    parser.add_argument("--normalizedProbability", help="Alert on records with a "
        + "normalized probablilty >= this", type=float, default=None)
    parser.add_argument("--timeout", help="The long poll timeout period", type=int, default=None)
    parser.add_argument("jobid", help="The job to alert on")
    return parser.parse_args()


def printHeader():
    print "Timestamp, Anomaly Score, Normalized Probablilty, URI, Results"

def printAlert(alert):

    if 'bucket' in alert:
        data = alert['bucket']
    else:
        data = alert['records']

    line = "{0}, {1}, {2}, {3}. {4}".format(alert['timestamp'],
                alert['anomalyScore'], alert['maxNormalizedProbability'],
                alert['uri'], data)

    print line


def main():

    setupLogging()

    args = parseArguments()
    job_id = args.jobid

    # Create the REST API client
    engine_client = EngineApiClient(args.host, BASE_URL, args.port)

    logging.info("Subscribing to job '" + job_id + "' for alerts")

    printHeader()

    while True:

        try:
            (http_status_code, response) = engine_client.alerts_longpoll(job_id,
                normalized_probability_threshold=args.normalizedProbability,
                anomaly_score_threshold=args.anomalyScore, timeout=args.timeout)
            if http_status_code != 200:
                print (http_status_code, json.dumps(response))
                break

            if response['timeout'] == False:
                printAlert(response)

        except KeyboardInterrupt:
            print "Exiting script..."

if __name__ == "__main__":
    main()

