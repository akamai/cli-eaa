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

from configparser import ConfigParser
import http.client as http_client

logger = logging.getLogger(__name__)


class EdgeGridConfig():

    parser = argparse.ArgumentParser(prog="akamai eaa",
                                     description='Process command line options.')

    def __init__(self, config_values, configuration, flags=None):
        parser = self.parser

        subparsers = parser.add_subparsers(dest='command', help='Main command')

        event_parser = subparsers.add_parser("log", aliases=["l"], help="Fetch log events")
        event_parser.add_argument('log_type', nargs='?', default="access",
                                  choices=['access', 'admin'], help="Log line type")
        event_parser.add_argument('--start', '-s', type=int, help="Start datetime (EPOCH)")
        event_parser.add_argument('--end', '-e', type=int, help="End datetime (EPOCH)")
        event_parser.add_argument('--output', '-o', help="Output file, default is stdout. Encoding is utf-8.")
        event_parser.add_argument('--tail', '-f', action='store_true', default=False,
                                  help="""Do not stop when most recent log is reached,
                                  but rather to wait for additional data to be appended to the input.""")

        search_parser = subparsers.add_parser('search', aliases=["s"], help='Search in EAA Application configurations')
        search_parser.add_argument('pattern', nargs='?')

        dir_parser = subparsers.add_parser('dir', aliases=['d'], help='Manage EAA directories')
        dir_parser.add_argument('directory_id', help="EAA Directory ID (e.g. dir://abcdefghi)", nargs='?')
        subsub = dir_parser.add_subparsers(dest="action", help='Directory action (default is: list)')
#        subsub.add_parser("list", help="List EAA directories")

        listgrp_parser = subsub.add_parser("list", help="List all groups existing in an EAA directory")
        listgrp_parser.add_argument('--groups', '-g', action='store_true', default=True, help="Display users")
        listgrp_parser.add_argument('--users', '-u', action='store_true', default=False, help="Display groups")
        listgrp_parser.add_argument('search_pattern', nargs='?', help="Search pattern")

        addgrp_parser = subsub.add_parser("addgroup", help="Add Group")
        addgrp_parser.add_argument(
            'dn',
            help="Distinguished Name (when existing "
                 "group in directory as string or @file "
                 "for multiple DNs, eg. \"CN=Support,"
                 "CN=Users,DC=CONTOSO,DC=NET\"")

        addovlgrp_parser = subsub.add_parser(
            "addovlgroup",
            help="Add Overlay Group")
        addovlgrp_parser.add_argument('group', help="Group Name")

        subsub.add_parser("sync", help="Synchronize directory")

        # New: akamai eaa app xyz add_dnsexception www.abcd.efg
        #      akamai eaa app xyz del_dnsexception www.abcd.efg
        app_parser = subparsers.add_parser('app', aliases=["a"], help='Manage EAA applications')
        app_parser.add_argument(dest='application_id', help="Application ID, AppGroup ID or '-'")
        subsub = app_parser.add_subparsers(dest="action", help='Application action')
        adddns_parser = subsub.add_parser("add_dnsexception", help="Add DNS Exception to tunnel-type client-app")
        adddns_parser.add_argument(dest="exception_fqdn", metavar='fqdn', nargs="+", help='DNS exception FQDN')
        deldns_parser = subsub.add_parser("del_dnsexception", help="Remove DNS Exception from tunnel-type client-app")
        deldns_parser.add_argument(dest="exception_fqdn",  metavar='fqdn', nargs="+", help='DNS exception FQDN')
        subsub.add_parser("deploy", help="Deploy the application")
        subsub.add_parser("update", help="Update an existing application")
        subsub.add_parser("create", help="Create a new application")
        subsub.add_parser("delete", help="Delete an application")
        subsub.add_parser("view", help="Dump application configuration (JSON)")
        subsub.add_parser("viewgroups", help="Dump application configuration (JSON)")
        subsub.add_parser("delgroup", help="Remove group from application, appgroup ID must provided")

        report_parser = subparsers.add_parser('report', aliases=["r"], help='EAA reports')
        report_parser.add_argument(dest='report_name', choices=['clients'], help="Report name")

        con_parser = subparsers.add_parser('connector', aliases=["c"], help='Manage EAA connectors')

        subparsers.add_parser('version', help='Display cli-eaa module version')

        parser.add_argument('--batch', '-b', default=False, action='store_true',
                            help='Batch mode, remove the extra header/footer in lists.')
        parser.add_argument('--verbose', '-v', default=False, action='count', help=' Verbose mode')
        parser.add_argument('--debug', '-d', default=False, action='count', help=' Debug mode (prints HTTP headers)')
        parser.add_argument('--edgerc', '-e', default='~/.edgerc', metavar='credentials_file',
                            help=' Location of the credentials file (default is %s)' % os.path.expanduser("~/.edgerc"))
        parser.add_argument('--section', '-c', default='default', metavar='credentials_file_section', action='store',
                            help=' Credentials file Section\'s name to use (\'default\' if not specified).')

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
        except Exception:
            sys.exit(1)

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
                err_msg = "ERROR: No section named %s was found in your %s file\n" % \
                          (configuration, arguments["edgerc"])
                err_msg += "ERROR: Please generate credentials for the script functionality\n"
                err_msg += "ERROR: and run 'python gen_edgerc.py %s' to generate the credential file\n" % configuration
                sys.exit(err_msg)
            for key, value in config.items(configuration):
                # ConfigParser lowercases magically
                if key not in arguments or arguments[key] is None:
                    arguments[key] = value
                else:
                    print("Missing configuration file.")
                    print("Run python gen_edgerc.py to get your credentials file set up "
                          "once you've provisioned credentials in Akamai Control Center.")
                    return None

        for option in arguments:
            setattr(self, option, arguments[option])

        if hasattr(self, 'eaa_api_host'):
            self.create_base_url()

    def create_base_url(self):
        self.base_url = "https://%s" % self.eaa_api_host

# end of file
