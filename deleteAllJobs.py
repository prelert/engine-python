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
Delete all the jobs in the Engine API. 
Request a list of jobs configured in the API then
delete them one at a time using the job id.

Be careful with this one you can't change your mind afterwards.
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


def parseArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", help="The Prelert Engine API host, defaults to "
        + HOST, default=HOST)
    parser.add_argument("--port", help="The Prelert Engine API port, defaults to "
        + str(PORT), default=PORT)
    
    return parser.parse_args()   


def main():
    args = parseArguments()
    host = args.host
    port = args.port
    base_url = BASE_URL

    # Create the REST API client
    engine_client = EngineApiClient(host, base_url, port)

    while True:
        (http_status_code, response) = engine_client.getJobs()
        if http_status_code != 200:
            print (http_status_code, json.dumps(response))
            break
        
        jobs = response['documents']        
        if (len(jobs) == 0):
            print "Deleted all jobs"
            break


        print "Deleting %d jobs" % (len(jobs)),

        for job in jobs:
            (http_status_code, response) = engine_client.delete(job['id'])
            if http_status_code != 200:
                print (http_status_code, json.dumps(response))
            else:
                sys.stdout.write('.')
                sys.stdout.flush()
        print

     
if __name__ == "__main__":
    main()    

