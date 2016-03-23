#!/usr/bin/env python
############################################################################
#                                                                          #
# Copyright 2014-2015 Prelert Ltd                                          #
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
"""
Example of how influencers can be queried from the Engine API in CSV format
using Python 2.6+ (including Python 3.x).  No extra modules are required beyond
those that come with a base Python install.

Usage:

python influencersToCsv.py <job> <server_hostname> [ <server_port> [ <result_limit> ] ]

The job ID and server hostname must be specified.  The port defaults to 8080
if not specified and the number of maximum number of results to 10000.

Influencers are returned in descending order of influencer anomaly score; the
most unusual will be at the top of the list.
"""

import csv
import json
import sys

try:
    # For Python 3.x
    from urllib.request import urlopen
except ImportError:
    # For Python 2.x
    from urllib2 import urlopen

if len(sys.argv) < 3:
    sys.stderr.write('Usage: %s <job> <server_hostname> [ <server_port> [ <result_limit> ] ]\n' % sys.argv[0])
    sys.exit(1)

job = sys.argv[1]
server = sys.argv[2]
port = 8080
if len(sys.argv) >= 4:
    port = sys.argv[3]
limit = 10000
if len(sys.argv) >= 5:
    limit = sys.argv[4]

url = 'http://%s:%s/engine/v2/results/%s/influencers?take=%s' % (server, port, job, limit)
response = urlopen(url).read()
json = json.loads(response.decode('utf-8'))
writtenHeader = False
csvWriter = csv.writer(sys.stdout)
for document in json['documents']:
    if not writtenHeader:
        csvWriter.writerow([ key for key in sorted(document) ])
        writtenHeader = True
    csvWriter.writerow([ str(document[key]) for key in sorted(document) ])

