Prelert Engine ELK Integration
==============================
These scripts serve as a connector between ELK (Elasticsearch-logstash-Kibana) 
and the Prelert Engine API. You can analyze your historical log data or query 
new log records as they are added to logstash and forward them to the Engine for 
analysis in real time.

Pre-requisites
--------------
* ELK is installed
* Engine API is installed
* The Engine Python client is installed 
    *  `python setup.py install`


Apache Web Server Access Logs Example
--------------------------------------
In this example we create an Engine API job to analyze Apache Web Server Access logs stored
in logstash. Here's an example of the access log format in this case the website visitor is Microsoft's Bingbot

    157.55.33.115 - - [30/May/2014:01:02:39 +0000] "GET / HTTP/1.1" 200 36633 "-" "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"

logstash has a standard *grok* pattern for access logs the files can be ingested 
with this configuration and stored in Elasticsearch

    input {
        file {
          path => "/path/to/access.log"
          type => "apache-access"
        }
    }

    filter {
      grok {
        match => [ "message", "%{COMBINEDAPACHELOG}" ]
      }
      date {
        match => [ "timestamp" , "dd/MMM/yyyy:HH:mm:ss Z" ]
      }
    }

    output {
        elasticsearch {}
    }

### Job Configuration 
The fields under analysis for the this job are the HTTP status code and the log's 
timestamp we are interested in cases where the total count of a particular 
HTTP status code in a bucket is much higher or lower than usual. 

The analysis is configured with a 300 seconds (5 minutes) *bucketSpan* and one 
detector (count by response).

    "analysisConfig" : { 
        "bucketSpan":300,
        "detectors":[{"function":"count","byFieldName":"response"}] 
    }

The data is in JSON format and the field containing the timestamp is called '@timestamp'

    "dataDescription" : {
        "format":"json",
        "timeField":"@timestamp", 
        "timeFormat":"yyyy-MM-dd'T'HH:mm:ss.SSSX"
    }

### Elasticsearch Query
Our configuration file also contains the Elasticsearch query to extract the log records.
The results must be ordered by timestamp earliest first as the Engine API expects 
records to be presented in that order. As we are only using the 'response' and '@timestamp'
fields the query returns only those.

    {
        "filter" : { "match_all" : {}},
        "sort":[{"@timestamp" : {"order":"asc"} }],
        "_source" : ["response", "@timestamp"]            
    }

### Connector Configuration
The config file must define a type this is the same as the logstash type and is 
used in Elasticsearch queries
    
    {
        "type" : "apache-access",
        ...
    }


Analyzing Stored Data
---------------------
Logstash puts each day's data into a separate index and names that index following 
the pattern 'logstash-YYYY.MM.DD'. When querying Elasticsearch for logstash records
the most efficient strategy is to search one index at a time and this is the approach
taken by the [elk_connector.py](elk_connector.py) script using the predictable logstash
index names. Start and end dates can be supplied as optional arguments on the command 
line otherwise the script finds the oldest index containing the configured data type 
and starts from there. 

####For help see
    python elk_connector.py --help

####Example
Using the configuration in 'configs/apache-access.json' analyze all data after April 1st 2014

    python elk_connector.py --start_date=2014-01-04 configs/apache-access.json


Analyzing Real Time Data
------------------------
The script [elk_connector_realtime.py](elk_connector_realtime.py) reads log records 
from logstash indexes in Elasticsearch and uploads them to the Prelert Engine in 
real time. By default the last 60 seconds of logs are read every 60 seconds this
can be changed by setting the '--update-interval' argument.

####For help see
    python realtime_logstash.py --help

####Example
Connect to the Elasticsearch cluster on host 'elasticsearch-server' and the Prelert
Engine API on 'prelert-server' sending the data to job 'XXXX'

    python realtime_logstash.py --es-host=elasticsearch-server
        --api-host=prelert-server --job-id=XXXX configs/syslog.json 
