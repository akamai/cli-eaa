# Python edgegrid module - CONFIG for EAA CLI module
""" 
 Copyright 2020 Akamai Technologies, Inc. All Rights Reserved.
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.

 You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
 
 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""

import sys
import os
import argparse
import logging

if sys.version_info[0] >= 3:
    # python3
    from configparser import ConfigParser
    import http.client as http_client
else:
    # python2.7
    from ConfigParser import ConfigParser
    import httplib as http_client

logger = logging.getLogger(__name__)

class EdgeGridConfig():

    parser = argparse.ArgumentParser(description='Process command line options.')

    def __init__(self, config_values, configuration, flags=None):
        parser = self.parser

        subparsers = parser.add_subparsers(dest="command", help='EAA object to manipulate')

        event_parser = subparsers.add_parser("log", help="Fetch last log lines")
        event_parser.add_argument('log_type', nargs='?', default="access", 
                                  choices=['access', 'admin'], help="Log line type")
        event_parser.add_argument('--start', '-s', type=int, help="Start datetime (EPOCH)")
        event_parser.add_argument('--end', '-e', type=int, help="End datetime (EPOCH)")
        event_parser.add_argument('--output', '-o', help="Output file, default is stdout")
        event_parser.add_argument('--tail', '-f', action='store_true', default=False, 
                                  help="""Do not stop when most recent log is reached, 
                                  but rather to wait for additional data to be appended to the input.""")
    
        parser.add_argument('--verbose', '-v', default=False, action='count', help=' Verbose mode')
        parser.add_argument('--debug', '-d', default=False, action='count', help=' Debug mode (prints HTTP headers)')
        parser.add_argument('--edgerc', '-e', default='~/.edgerc', metavar='credentials_file', 
                            help=' Location of the credentials file (default is ~/.edgerc)')
        parser.add_argument('--section', '-c', default='default', metavar='credentials_file_section', action='store', 
                            help=' Credentials file Section\'s name to use')

        if flags:
            for argument in flags.keys():
                parser.add_argument('--' + argument, action=flags[argument])

        arguments = {}
        for argument in config_values:
            if config_values[argument]:
                if config_values[argument] == "False" or config_values[argument] == "True":
                    parser.add_argument('--' + argument, action='count')
                parser.add_argument('--' + argument)
                arguments[argument] = config_values[argument]

        try:
            args = parser.parse_args()
        except:
            sys.exit()

        arguments = vars(args)

        if arguments['debug']:
            http_client.HTTPConnection.debuglevel = 1
            logging.basicConfig()
            logging.getLogger().setLevel(logging.DEBUG)
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True

        if "section" in arguments and arguments["section"]:
            configuration = arguments["section"]

        arguments["edgerc"] = os.path.expanduser(arguments["edgerc"])

        if os.path.isfile(arguments["edgerc"]):
            config = ConfigParser()
            config.readfp(open(arguments["edgerc"]))
            if not config.has_section(configuration):
                err_msg = "ERROR: No section named %s was found in your %s file\n" % (configuration, arguments["edgerc"])
                err_msg += "ERROR: Please generate credentials for the script functionality\n"
                err_msg += "ERROR: and run 'python gen_edgerc.py %s' to generate the credential file\n" % configuration
                sys.exit( err_msg )
            for key, value in config.items(configuration):
                # ConfigParser lowercases magically
                if key not in arguments or arguments[key] is None:
                    arguments[key] = value
                else:
                    print("Missing configuration file.  Run python gen_edgerc.py to get your credentials file set up once you've provisioned credentials in LUNA.")
                    return None

        for option in arguments:
            setattr(self, option, arguments[option])

        self.create_base_url()

    def create_base_url(self):
        self.base_url = "https://%s" % self.eaa_api_host