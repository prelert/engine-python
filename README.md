engine-python
=============

A Python HTTP client to the Prelert Engine REST API.
Use the client to create jobs, stream data to them and review the results

Running the Examples
---------------------
All the example scripts will run from the root directory of this repository 
otherwise add this directory to your `PYTHONPATH` environment variable or copy
the `prelert` folder to you Python `site-packages` directory. 
The client uses the standard json, httplib and logging packages no additional
dependencies are required.

Using the Client
-----------------
The easiest way is to walk you through this annotated tutorial.
See the file [tutorial/engineApiTutorial.py] and example data [data/flightcentre.csv](data/flightcentre.csv)

Create the client and make a HTTP connection to the API server
Fire up your Python interpreter and paste

    from prelert.engineApiClient import EngineApiClient
    engine_client = EngineApiClient(host='localhost', base_url='/engine/v0.3', port=8080)

The job configuration is a JSON document

    job_config =  '{ \
                    "analysisConfig" : {\
                    "bucketSpan":3600,\
                    "detectors" :[{"fieldName":"responsetime","byFieldName":"airline"}] },\
                    "dataDescription" : {"fieldDelimiter":",", "timeField":"time", "timeFormat":"yyyy-MM-dd\'T\' HH:mm:ssX"}\
                   }'
    (http_status_code, response) = engine_client.createJob(job_config)

    import json
    print (http_status_code, json.dumps(response))
    (201, '{"id": "20140515150739-00002"}')

*createJob* returns a document with a single `id` field this is the `job id` of the new job.

Every client call returns a tuple *(http_status_code, response)* use the *http_status_code*
to determine the sucess of the operation, if the code is not one of the 2XX Success codes
response will be an object containing an error message.

As an example try creating a new job with an invalid configuration that does not define 
any detectors.

    bad_job_config = '{\
                      "analysisConfig" : {"bucketSpan":3600 },\
                      "dataDescription" : {"fieldDelimiter":",", "timeField":"time", "timeFormat":"yyyy-MM-dd\'T\'HH:mm:ssX"}\
                      }'

    engine_client = EngineApiClient(host='localhost', base_url='/engine/v0.3', port=8080)
    (http_status_code, response) = engine_client.createJob(bad_job_config)

    if http_status_code != 201:
        print (http_status_code, json.dumps(response))
    
    (400, '{"errorCode": 10107, "message": "No detectors configured"}')

and an informative error message reminds us to configure some detectors next time.
For more information on the possible error codes see the Engine API documentation.

Once we have a properly configured job we can upload data to it first let's revisit 
the configuration.
    
    "dataDescription" : {"fieldDelimiter":",", "timeField":"time", "timeFormat"="yyyy-MM-dd HH:mm:ssX"}

This line specifies that our data is in a delimited format (the default), the fields are
separated by ',' and there is a field 'time' containing a timestamp in the Java SimpleDateFormat 
'yyyy-MM-dd'T'HH:mm:ssX'.

Here's an example of the data:
> airline,responsetime,sourcetype,time  
> DJA,622,flightcentre,2012-10-21T13:00:00+0000  
> JQA,1742,flightcentre,2012-10-21T13:00:01+0000  
> GAL,5339,flightcentre,2012-10-21T13:00:02+0000  
> GAL,3893,flightcentre,2012-10-21T13:00:03+0000  

Create a job with our previously defined configuration   

    engine_client = EngineApiClient(host='localhost', base_url='/engine/v0.3', port=8080)  
    (http_status_code, response) = engine_client.createJob(job_config)  

    if http_status_code != 201:
        print (http_status_code, json.dumps(response))


The *job_id* will be used in all future method calls

Open the csv file and upload it to the Engine

    csv_data_file = open('data/flightcentre.csv', 'rb')
    (http_status_code, response) = engine_client.upload(job_id, csv_data_file)
    if http_status_code != 202:
        print (http_status_code, json.dumps(response)) # !error

The *upload* function accepts an open file object or a string.

Close the job to indicate that there is no more data to upload

    (http_status_code, response) = engine_client.close(job_id)
    if http_status_code != 202:
        print (http_status_code, json.dumps(response)) # !error

Now get all of the result buckets using one of the clients _bucket_ functions and 
print the anomaly scores

    (http_status_code, response) = engine_client.getAllBuckets(job_id)
    if http_status_code != 200:
        print (http_status_code, json.dumps(response))
    else:
        print "Date,BucketId,AnomalyScore"
        for bucket in response:                                
            print "{0},{1},{2}".format(bucket['timestamp'], bucket['anomalyScore']) 

You can also request buckets by time

    (http_status_code, response) = engine_client.getBucketsByDate(job_id=job_id,
        start_date='2012-10-22T07:00:00Z', end_date='2012-10-22T09:00:00Z')
    if http_status_code != 200:
        print (http_status_code, json.dumps(response))
    else:
        print "Date,AnomalyScore"
        for bucket in response:                                
            print "{0},{1}".format(bucket['timestamp'], bucket['anomalyScore'])  

