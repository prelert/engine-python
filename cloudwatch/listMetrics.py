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
Connects the Amazon CloudWatch and prints a list of all the available
metrics. Useful for testing connection settings.

The script has one mandatory argument - the path to a config filec
containing the AWS connection settings. The file should have the following
propteries:

    region=REGION
    aws_access_key_id=YOUR_ACCESS_ID
    aws_secret_access_key=YOUR_SECRET_KEY

Where REGION is one of us-east-1, eu-west-1, etc

'''

import argparse
import ConfigParser
import StringIO

import boto.ec2
import boto.ec2.cloudwatch


def parseArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="The AWS connection parameters.")

    return parser.parse_args()


def main():

    args = parseArguments()

    # read the config file
    config = ConfigParser.RawConfigParser()
    try:
        # insert a section header into the config so
        # ConfigParser will read it without complaint
        with open(args.config, "r") as config_file:
            ini_str = '[root]\n' + config_file.read()
            ini_fp = StringIO.StringIO(ini_str)
            config.readfp(ini_fp)
    except IOError:
        print "Error opening file " + args.file
        return


    try:
        region = config.get('root', 'region')
        access_id = config.get('root', 'aws_access_key_id')
        secret_key = config.get('root', 'aws_secret_access_key')
    except ConfigParser.NoOptionError as e:
        print e
        return

    # AWS CloudWatch connection
    cloudwatch_conn = boto.ec2.cloudwatch.connect_to_region(region,
                 aws_access_key_id=access_id,
                 aws_secret_access_key=secret_key)


    #metrics = cloudwatch_conn.list_metrics()
    metrics = cloudwatch_conn.list_metrics(namespace='AWS/EC2')
    for m in metrics:
         print m.name, m.namespace, m.dimensions



if __name__ == "__main__":
    main()   
