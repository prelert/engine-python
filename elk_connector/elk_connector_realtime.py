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
"""
This script reads log records from logstash indexes in elasticsearch
and uploads them to the Prelert Engine. Logs are read in real-time 
by default the last 60 seconds of logs are read every 60 seconds, this
can be changed by setting the '--update-interval' argument.

The program takes a number of optional arguments for the Engine 
API and elasticsearch connection settings the only required argument 
is the path to a config file containing the Engine Job configuration 
and the elasticsearch query. If a job id is provided then the logs 
are sent to that job else a new job is created. 

The script attempts to add a date range filter for the real-time date 
arguments to the elasticsearch query defined in the config file, if it 
cannot because 'filter' and 'post_filter' are already defined then
it raises an error. 

The program will indefinitely, interrupt it with Ctrl C and the
script will close the API analytics Job and exit gracefully. 

See:
    python elk_connector_realtime.py --help

Example:  
    python elk_connector_realtime.py --es-host=elasticsearchserver
        --api-host=prelertserver --job-id=jobid configs/syslog.json 
"""

import argparse
from datetime import datetime, time, timedelta, tzinfo
import json
import logging
import os
import sys
import time

import elasticsearch.exceptions
from elasticsearch import Elasticsearch
from prelert.engineApiClient import EngineApiClient


# Elasticsearch connection settings
ES_HOST = 'localhost'
ES_PORT = 9200

# Prelert Engine API connection prarams
API_HOST = 'localhost'
API_PORT = 8080
API_BASE_URL = 'engine/v1'

# The maximum number of documents to request from
# Elasticsearch in each query
MAX_DOC_TAKE = 5000

# The update interval in seconds
# elasticsearch is queried with this periodicity
UPDATE_INTERVAL = 60


class UTC(tzinfo):
    """
    UTC timezone class
    """
 
    def utcoffset(self, dt):
        return timedelta(0)
 
    def tzname(self, dt):
        return "UTC"
 
    def dst(self, dt):
        return timedelta(0)


def setupLogging():
    """
    Log to console
    """    
    logging.basicConfig(level=logging.WARN,format='%(asctime)s %(levelname)s %(message)s')

def parseArguments():
    parser = argparse.ArgumentParser()

    parser.add_argument("file", 
                help="Read the configuration from the specified file")
    parser.add_argument("--es-host", help="The host machine Elasticsearch is \
        running on, defaults to '" + ES_HOST + "'", default=ES_HOST, dest="es_host")
    parser.add_argument("--es-port", help="The Elasticsearch HTTP port, defaults to " 
        + str(ES_PORT), default=ES_PORT, dest="es_port")
    parser.add_argument("--api-host", help="The Prelert Engine API host, defaults to "
        + API_HOST, default=API_HOST, dest="api_host")    
    parser.add_argument("--api-port", help="The Prelert Engine API port, defaults to " 
        + str(API_PORT), default=API_PORT, dest="api_port")
    parser.add_argument("--job-id", help="Send data to this job. If not set a \
        new job will be created.", default=None, dest="job_id")    
    parser.add_argument("--update-interval", help="The period between each \
        each cycle of querying and uploading data", type=int,
        default=UPDATE_INTERVAL, dest="update_interval")


    return parser.parse_args()   

def elasticSearchDocsToDicts(hits):
    """
    Convert the Elasticsearch hits into an list of dict objects
    In this case we use the '_source' object as the desired fields
    were set in the query.
    """

    objs = []
    for hit in hits:
        objs.append(hit['_source']) 

    return objs

def logstashIndex(date):
    """
    Return the logstash index name for the given date

    Logstash index names are in the format: 'logstash-YYYY.MM.DD'
    """

    return "logstash-" + date.strftime("%Y.%m.%d")


def insertDateRangeFilter(query):
    """
    Add a date range filter on the '@timestamp' field either as 
    a 'filter' or 'post_filter'. If both 'filter' and 'post_filter'
    are already defined then an RuntimeError is raised as the 
    date filter cannot be inserted into the query.

    The date range filter will look like either

        "filter" : {"range" : { "@timestamp" : { "gte" : "start-date",
            "lt" : "end-date"} } }
    or

        "post_filter" : {"range" : { "@timestamp" : { "gte" : "start-date",
            "lt" : "end-date"} } }

    where 'start-date' and 'end-date' literals will be replaced by 
    the actual timestamps in the query. 
    """

    dates = {'gte' : 'start-date', 'lt' : 'end-date'}
    timestamp = {'@timestamp' : dates}
    range_ = {'range' : timestamp}
    
    if not 'filter' in query:
        query['filter'] = range_
    elif not 'post_filter' in query:
        query['post_filter'] = range_
    else:
        raise RuntimeError("Cannot add a 'filter' or 'post_filter' \
date range to the query")

    return query


def replaceDateArgs(query, query_start_time, query_end_time):
    """
    Replace the date arguments in the range filter of the query.
    """

    if not 'filter' in query:
        query['filter']['range']['@timestamp']['gte'] = query_start_time.isoformat()
        query['filter']['range']['@timestamp']['lt'] = query_end_time.isoformat()
    else:
        query['post_filter']['range']['@timestamp']['gte'] = query_start_time.isoformat()
        query['post_filter']['range']['@timestamp']['lt'] = query_end_time.isoformat()

    return query


def main():

    setupLogging()
    args = parseArguments()

    # read the config file
    try:
        with open(args.file, "r") as config_file:
            config = json.load(config_file)
    except IOError:
        print "Error opening file " + args.file
        return
  

    # The ElasticSearch client
    es_client = Elasticsearch(args.es_host + ":" + str(args.es_port))

    # The REST API client
    engine_client = EngineApiClient(args.api_host, API_BASE_URL, args.api_port)

    job_id = args.job_id
    if job_id == None:
        (http_status, response) = engine_client.createJob(json.dumps(config['job_config']))
        job_id = response['id']  
        print "Created job with id " + str(job_id)

    print "Using job id " + job_id

    data_type = config['type']
    raw_query = insertDateRangeFilter(config['search'])
    

    timezone = UTC()
    doc_count = 0    
    try:
        query_end_time = datetime.now(timezone) - timedelta(seconds=args.update_interval)
        while True:
            query_start_time = query_end_time
            query_end_time = datetime.now(timezone)
            query_str = json.dumps(replaceDateArgs(raw_query, query_start_time, 
                query_end_time)) 
            index_name = logstashIndex(query_start_time)        

            skip = 0
            try:
                # Query the documents from ElasticSearch and write to the Engine
                hits = es_client.search(index=index_name, doc_type=data_type, 
                    body=query_str, from_=skip, size=MAX_DOC_TAKE)
            except elasticsearch.exceptions.NotFoundError:
                print "Error: missing logstash index '" + index_name + "'"
                

            # upload to the API
            content = json.dumps(elasticSearchDocsToDicts(hits['hits']['hits'])) 
            
            (http_status, response) = engine_client.upload(job_id, content)
            if http_status != 202:
                print "Error uploading log content to the Engine"
                print http_status, json.dumps(response)
                

            doc_count += len(hits['hits']['hits'])                 

            # get any other docs
            hitcount = int(hits['hits']['total'])
            while hitcount > (skip + MAX_DOC_TAKE):    
                skip += MAX_DOC_TAKE
                hits = es_client.search(index=index_name, doc_type=data_type, 
                    body=query_str, from_=skip, size=MAX_DOC_TAKE)

                content = json.dumps(elasticSearchDocsToDicts(hits['hits']['hits']))

                (http_status, response) = engine_client.upload(job_id, content)
                if http_status != 202:
                    print "Error uploading log content to the Engine"
                    print json.dumps(response)
                    

                doc_count += len(hits['hits']['hits']) 

            print "Uploaded {0} records".format(str(doc_count))

            duration = datetime.now(timezone) - query_end_time
            sleep_time = max(args.update_interval - duration.seconds, 0)
            print "sleeping for " + str(sleep_time) + " seconds"

            if sleep_time > 0.0:                
                time.sleep(sleep_time)

  
    except KeyboardInterrupt:
        print "Interrupt caught closing job..."

    

    engine_client.close(job_id)


if __name__ == "__main__":
    main()    

