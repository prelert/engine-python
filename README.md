engine-python
=============

A Python HTTP client to the Prelert Anomaly Detective Engine REST API. The client creates analysis jobs, streams data to them and queries the results.

Prior to using the client, the Engine API needs to be installed and setup. Please follow these steps:

- Have a read of our documentation: http://www.prelert.com/docs/engine_api/latest
- Download and install the Anomaly Detective Engine API from here: http://www.prelert.com/reg/anomaly-detective-engine-api.html
- We recommend you try our quick start example: http://www.prelert.com/docs/engine_api/latest/quick-start.html

If you are already familiar with connecting to the Engine API, then please check out:

- [Elasticsearch ELK Connector](elk_connector)
- [AWS CloudWatch Connector](cloudwatch)

Running the Examples
---------------------
First install the client using the standard setup script:

    python setup.py install

The client uses the standard json, httplib and logging packages no additional
dependencies are required. The example scripts use the `argparse` module that
was added to Python in version 2.7.

Using the Client
-----------------
The easiest way is to walk you through this annotated example.
See the file [simpleEngineApiExample.py](simpleEngineApiExample.py) and download the example data
from  [http://s3.amazonaws.com/prelert_demo/farequote.csv](http://s3.amazonaws.com/prelert_demo/farequote.csv). To run the full example invoke:

    python simpleEngineApiExample.py farequote.csv

Your first act is to create the client and make a HTTP connection to the API server

    from prelert.engineApiClient import EngineApiClient
    engine_client = EngineApiClient(host='localhost', base_url='/engine/v0.3', port=8080)

Before you can create a job the configuration must be defined.

    job_config =  '{ \
                    "analysisConfig" : {\
                    "bucketSpan":3600,\
                    "detectors" :[{"fieldName":"responsetime","byFieldName":"airline"}] },\
                    "dataDescription" : {"fieldDelimiter":",", "timeField":"time", "timeFormat":"yyyy-MM-dd HH:mm:ssX"}\
                   }'
    (http_status_code, response) = engine_client.createJob(job_config)

    import json
    print (http_status_code, json.dumps(response))
    (201, '{"id": "20140515150739-00002"}')

*createJob* returns a document with a single `id` field this is the `job id` of the new job.

Every client call returns a tuple *(http_status_code, response)* use the *http_status_code*
to determine the sucess of the operation, if the code is not one of the 2XX Success codes
response will be an object containing an error message.

As an example try creating a new job with an invalid configuration - this one does not define 
any detectors.

    bad_job_config = '{\
                      "analysisConfig" : {"bucketSpan":3600 },\
                      "dataDescription" : {"fieldDelimiter":",", "timeField":"time", "timeFormat":"yyyy-MM-dd HH:mm:ssX"}\
                      }'

    engine_client = EngineApiClient(host='localhost', base_url='/engine/v0.3', port=8080)
    (http_status_code, response) = engine_client.createJob(bad_job_config)

    if http_status_code != 201:
        print (http_status_code, json.dumps(response))
    
    (400, '{"errorCode": 10107, "message": "No detectors configured"}')

and an informative error message reminds us to configure some detectors next time.
For more information on the possible error codes see the Engine API documentation.

Once we have a properly configured job we can upload data to it first let's revisit part of
the configuration.
    
    "dataDescription" : {"fieldDelimiter":",", "timeField":"time", "timeFormat"="yyyy-MM-dd HH:mm:ssX"}

This line specifies that our data is in a delimited format (the default), the fields are
separated by ',' and there is a field 'time' containing a timestamp in the Java SimpleDateFormat 
'yyyy-MM-dd HH:mm:ssX'.

Here's an example of the data:
> time,airline,responsetime,sourcetype
> 2013-01-28 00:00:00Z,AAL,132.2046,farequote  
> 2013-01-28 00:00:00Z,JZA,990.4628,farequote  
> 2013-01-28 00:00:00Z,JBU,877.5927,farequote  
> 2013-01-28 00:00:00Z,KLM,1355.4812,farequote  

Create a job with our previously defined configuration   

    engine_client = EngineApiClient(host='localhost', base_url='/engine/v0.3', port=8080)  
    (http_status_code, response) = engine_client.createJob(job_config)  

    if http_status_code == 201:
        job_id = response['id']


The *job_id* will be used in all future method calls

Open the csv file and upload it to the Engine

    csv_data_file = open('data/farequote.csv', 'rb')
    (http_status_code, response) = engine_client.upload(job_id, csv_data_file)
    if http_status_code != 202:
        print (http_status_code, json.dumps(response)) # !error

The *upload* function accepts either an open file object or a string.

Close the job to indicate that there is no more data to upload

    (http_status_code, response) = engine_client.close(job_id)
    if http_status_code != 202:
        print (http_status_code, json.dumps(response)) # !error

Now get all of the result buckets using one of the clients _getBuckets_ functions and 
print the anomaly scores

    (http_status_code, response) = engine_client.getAllBuckets(job_id)
    if http_status_code != 200:
        print (http_status_code, json.dumps(response))
    else:
        print "Date,AnomalyScore"
        for bucket in response:                                
            print "{0},{1}".format(bucket['timestamp'], bucket['anomalyScore']) 

You can also request buckets by time

    (http_status_code, response) = engine_client.getBucketsByDate(job_id=job_id,
        start_date='2012-10-22T07:00:00Z', end_date='2012-10-22T09:00:00Z')
    if http_status_code != 200:
        print (http_status_code, json.dumps(response))
    else:
        print "Date,AnomalyScore"
        for bucket in response:                                
            print "{0},{1}".format(bucket['timestamp'], bucket['anomalyScore'])  

