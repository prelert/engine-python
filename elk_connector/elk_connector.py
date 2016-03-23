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
This script will extract historical log records from Elastissearch logstash
and upload them to the Prelert Engine API. The program takes
a number of arguments for the Engine API and Elasticsearch connection 
settings and optional start and end dates to limit the period begin 
analysed. The only required argument is the path to a config file 
containing the Engine Job configuration and the elasticsearch query. 

See:
    python elk_connector.py --help

Example:    
    Read all the data from the beginning of January 2014 and 
    upload it to the API server running on host 'api.server'

    python elk_connector.py --start_date=2014-01-01 --api-host=api.server configs/apache-access.json
"""

import argparse
from datetime import datetime, timedelta
import json
import logging
import os
import sys

import elasticsearch.exceptions
from elasticsearch import Elasticsearch
from prelert.engineApiClient import EngineApiClient


# Elasticsearch connection settings
ES_HOST = 'localhost'
ES_PORT = 9200

# Prelert Engine API connection prarams
API_HOST = 'localhost'
API_PORT = 8080
API_BASE_URL = 'engine/v2'


# The maximum number of documents to request from
# Elasticsearch in each query
MAX_DOC_TAKE = 5000


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
    parser.add_argument("--start-date", help="Pull data from this date, if not \
        set the search starts with the oldest Logstash index. Dates must be in \
        YYYY-MM-DD format", default=None, dest="start_date")
    parser.add_argument("--end-date", help="Pull data up to this date, if not \
        set all indexes from --start-date are searched. Dates must be in \
        YYYY-MM-DD format", default=None, dest="end_date")


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

def nextLogStashIndex(start_date, end_date):
    """
    Generator method for listing all the Logstash index names
    between 2 dates. The method returns when then index for 
    end_date is generated.

    Logstash index names are in this format: 'logstash-YYYY.MM.DD'
    """

    yield "logstash-" + start_date.strftime("%Y.%m.%d")

    one_day = timedelta(days=1)
    while True:
        start_date = start_date + one_day
        if start_date > end_date:
            break

        yield "logstash-" + start_date.strftime("%Y.%m.%d")


def findDateOfFirstIndex(es_client, type, query):
    """
    Query for 1 document from all indicies (he query should be sorted
    in time order) the index the document belongs to is the start index.

    Returns the date of the first index or None if no documents are found
    """

    hits = es_client.search(index="_all", doc_type=type, 
            body=query, from_=0, size=1)

    if len(hits['hits']['hits']) > 0:
        date_str = hits['hits']['hits'][0]['_index'].lstrip("logstash-")     
        
        return datetime.strptime(date_str, "%Y.%m.%d")
    else:
        return None



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


    # default start date is None meaning 'all time'
    start_date = None
    if args.start_date != None:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")

    # default end date is today
    end_date = datetime.today()
    if args.end_date != None:
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
   

    # The ElasticSearch client
    es_client = Elasticsearch(args.es_host + ":" + str(args.es_port))

    data_type = config['type']
    search_body = json.dumps(config['search'])

    # If no start date find the first logstash index containing our docs
    if start_date == None:        
        start_date = findDateOfFirstIndex(es_client, data_type, search_body)
        if start_date == None:
            print "No documents found with the query " + search_body
            return

    # The REST API client
    engine_client = EngineApiClient(args.api_host, API_BASE_URL, args.api_port)
    (http_status, response) = engine_client.createJob(json.dumps(config['job_config']))
    if http_status != 201:
        print "Error creatting job"
        print http_status, json.dumps(response)
        return


    job_id = response['id']  
    print "Created job with id " + str(job_id)

    doc_count = 0
    for index_name in nextLogStashIndex(start_date, end_date):

        print "Reading from index " + index_name

        skip = 0
        try:
            # Query the documents from ElasticSearch and write to the Engine
            hits = es_client.search(index=index_name, doc_type=data_type, 
                body=search_body, from_=skip, size=MAX_DOC_TAKE)
        except elasticsearch.exceptions.NotFoundError:
            # Index not found try the next one
            continue

        # upload to the API
        content = json.dumps(elasticSearchDocsToDicts(hits['hits']['hits']))        
        (http_status, response) = engine_client.upload(job_id, content)
        if http_status != 202:
            print "Error uploading log content to the Engine"
            print http_status, json.dumps(response)
            continue

        doc_count += len(hits['hits']['hits']) 

        # get any other docs
        hitcount = int(hits['hits']['total'])
        while hitcount > (skip + MAX_DOC_TAKE):    
            skip += MAX_DOC_TAKE
            hits = es_client.search(index=index_name, doc_type=data_type, 
                body=search_body, from_=skip, size=MAX_DOC_TAKE)

            content = json.dumps(elasticSearchDocsToDicts(hits['hits']['hits']))        
            (http_status, response) = engine_client.upload(job_id, content)
            if http_status != 202:
                print json.dumps(response)
                continue

            doc_count += len(hits['hits']['hits']) 


        print "Uploaded {0} records".format(str(doc_count))
        
    (http_status, response) = engine_client.close(job_id)
    if http_status != 202:
        print "Error closing job"
        print http_status, json.dumps(response)
        return
    print "{0} records successfully written to job {1}".format(str(doc_count), job_id)


if __name__ == "__main__":
    main()    

