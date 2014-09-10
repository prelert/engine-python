Prelert - Data Analytics for AWS CloudWatch
==============================

Prelert's analytics provides fast insights into your machine data. This simple example
shows how to use Prelert Anomaly Detection for your CloudWatch monitoring data.


Pre-requisites and Installation
--------------
* The Prelert Engine API, download a free trial from [here](http://www.prelert.com/reg/beta-signup.html)
* The Prelert Engine API [Python client](https://github.com/prelert/engine-python)
* [Boto](https://github.com/boto/boto) the Python interface to Amazon Web Services
* An Amazon Web Services account and your access details

Install the Prelert Python client from GitHub

    git clone https://github.com/prelert/engine-python.git
    python setup.py install

Boto can either be installed using `pip`

    pip install boto

or cloned from GitHub

    git clone git://github.com/boto/boto.git
    cd boto
    python setup.py install


Connecting to Amazon CloudWatch
----------
First create a configuration file containing your Amazon access ID and key e.g:

    region=REGION
    aws_access_key_id=YOUR_ACCESS_ID
    aws_secret_access_key=YOUR_SECRET_KEY

Where REGION is one of us-east-1, eu-west-1, etc

Save the configuration as aws_access.conf and test the connection parameters using 
the [listMetrics.py](listMetrics.py) script

    python listMetrics.py aws_access.conf

If the script reports an error instead of a list of metrics, like the example below, check your connection settings.

    DiskReadBytes AWS/EC2 {u'InstanceId': [u'i-d9789exx']}
    DiskWriteBytes AWS/EC2 {u'InstanceId': [u'i-4b8c47xx']}
    NetworkIn AWS/EC2 {u'InstanceId': [u'i-4b8c47xx']}
    ...

Metric Data
------------
CloudWatch metrics have a name, namespace and a list of dimensions. In this case we
are only interested in metrics from the 'AWS/EC2' namespace

    Metric Name,    Namespace, Dimensions
    NetworkIn,      AWS/EC2,   {'InstanceId': [u'i-baaa95xx']}
    CPUUtilization, AWS/EC2,   {'InstanceId': [u'i-140862xx']}

For a particular instance/metric combination Amazon provide an API call to get the
metrics statistics, in this case the average value was requested for the *CPUUtilization* metric 
returning a list of datapoints:

    {'Timestamp': datetime.datetime(2014, 9, 10, 10, 26), 'Average': 1.8, 'Unit': 'Percent'}
    {'Timestamp': datetime.datetime(2014, 9, 10, 10, 31), 'Average': 1.0, 'Unit': 'Percent'}
    ...

The data is then formatted in a manner suitable for uploading to the Prelert Engine.

    {"timestamp":"2014-09-10T11:05:00+00:00", "instance":"i-1a1743xx", "metric_name":"CPUUtilization", "Average":80.01}
    {"timestamp":"2014-09-10T11:05:00+00:00", "instance":"i-140862xx", "metric_name":"NetworkIn", "Average":8722.6}
    {"timestamp":"2014-09-10T11:05:00+00:00", "instance":"i-1a1743xx", "metric_name":"StatusCheckFailed", "Average":0.0}
    {"timestamp":"2014-09-10T11:05:00+00:00", "instance":"i-1a1743xx", "metric_name":"DiskWriteOps", "Average":0.0}
    {"timestamp":"2014-09-10T11:05:00+00:00", "instance":"i-1a1743xx", "metric_name":"DiskReadOps", "Average":1.0}


Job Configuration
------------------

The Prelert Engine job is defined as having one detector configured to analyze the mean of the field named 
'Average' by the field 'metric_name' where the value of 'metric_name' is one of the 
AWS metrics i.e. CPUUtilization, DiskWriteOps, etc. The analysis is partitioned by AWS instance ID.
`bucketSpan` is set to 300 seconds, which should be set to the same as the CloudWatch reporting interval.

    "analysisConfig" : {
        "bucketSpan":' 300,
        "detectors" : "function":"mean","fieldName":"Average","byFieldName":"metric_name","partitionFieldName":"instance"}] 
    }

The job's dataDescription instructs the Engine that the data is in JSON format and how to parse the timestamp

    "dataDescription" : {"format":"JSON","timeField":"timestamp","timeFormat":"yyyy-MM-dd'T'HH:mm:ssX"} 


With the metric data in a suitable format and the job configured we are now ready to monitor CloudWatch data.

Analyzing Real Time Data
-------------------------

[cloudWatchMetrics.py](cloudWatchMetrics.py) requires one argument - the AWS connection file created previously.

    python cloudWatchMetrics.py aws_access.conf

In this mode the script will create a new job then run in an infinite loop and 5 minutes 
it will extract the previous 5 minutes of metric values from CloudWatch then upload this data to the Prelert Engine API. 
To send the data to a previously defined job use the *--job-id* option:

    python cloudWatchMetrics.py --job-id=cloudwatch aws_access.conf

To stop to process send press Ctrl-C and the script will catch the interrupt then gracefully exit after closing the running job.


Analyzing Stored Data
----------------------
If you wish to analyse historical data stored in CloudWatch the script accepts *--start-date* and *--end-date* 
with the dates in YYYY-MM-DD format

    python cloudWatchMetrics.py --start-date=2014-09-1 --end-date=2014-09-08 aws_access.conf

The script will exit once it has queried the all the data for that time period and analysed it.

*Note that the script assumes a default host and port for the Engine API, you can specify different
settings using the *--api-host* and *--api-port* settings.

    python cloudWatchMetrics.py --api-host=my.server --api-port=8000 aws_access.conf


Analytic Results
-----------------
Whether running in real time or historical mode the results of Prelert's analysis are made available once the
data has been processed. Review the results in the Jobs Dashboard (typically hosted at http://localhost:8080/dashboard/index.html#/dashboard/file/prelert_api_jobs.json) or directly through the API. For more information about the API results format see the [API reference](http://www.prelert.com/docs/engine_api/1.0/results.html)
