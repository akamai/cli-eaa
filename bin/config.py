"""
 Copyright 2022 Akamai Technologies, Inc. All Rights Reserved.
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

# Python edgegrid module - CONFIG for EAA CLI module

import os
import argparse

from configparser import ConfigParser

import _paths
from error import rc_error, cli_exit_with_error


class EdgeGridConfig():

    parser = argparse.ArgumentParser(prog="akamai eaa",
                                     description='Enterprise Application Access (EAA) for Akamai CLI')

    def __init__(self, config_values, configuration, flags=None):
        parser = self.parser

        subparsers = parser.add_subparsers(dest='command', help='Main command')

        event_parser = subparsers.add_parser("log", aliases=["l"], help="Fetch log events")
        event_parser.add_argument('log_type', nargs='?', default="access",
                                  choices=['access', 'admin'], help="Log line type")
        event_parser.add_argument('--start', '-s', type=int, help="Start datetime (EPOCH)")
        event_parser.add_argument('--end', '-e', type=int, help="End datetime (EPOCH)")
        event_parser.add_argument('--output', '-o', help="Output file, default is stdout. Encoding is utf-8.")
        event_parser.add_argument('--json', '-j', action="store_true", default=False,
                                  help="Output as JSON instead of raw line")
        event_parser.add_argument('--limit', type=int, default=5000,
                                  help="Size of logs to fetch in one API call. Max supported 5000")
        event_parser.add_argument('--delay', type=int, default=600,
                                  help="Log delay is seconds, minimum is 600s")
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
        syncgrp_parser = subsub.add_parser("syncgroup", help="Synchronize group")
        syncgrp_parser.add_argument('group_uuid', help="Group UUID e.g. group://abcedf")
        # mininterval | Undocumented argument
        # Group synchronization will be ignored if the last request
        # was performed before this amount of time in second. Use 0
        # to force the synchronization. Default is 1800 seconds (30 minutes)
        syncgrp_parser.add_argument('--mininterval', '-i', type=int, default=1800, help=argparse.SUPPRESS)
        # retry | Undocumented argument
        # Number of retry allowed if the sync command fails. Default: 0
        syncgrp_parser.add_argument("--retry", "-r", type=int, default=0, help=argparse.SUPPRESS)
        # New: akamai eaa app xyz add_dnsexception www.abcd.efg
        #      akamai eaa app xyz del_dnsexception www.abcd.efg
        app_parser = subparsers.add_parser('app', aliases=["a"], help='Manage EAA applications')
        app_parser.add_argument(dest='application_id', help="Application ID, AppGroup ID or '-'")
        subsub = app_parser.add_subparsers(dest="action", help='Application action')
        # DNS exception add/remove
        adddns_parser = subsub.add_parser("add_dnsexception", help="Add DNS Exception to tunnel-type client-app")
        adddns_parser.add_argument(dest="exception_fqdn", metavar='fqdn', nargs="+", help='DNS exception FQDN')
        deldns_parser = subsub.add_parser("del_dnsexception", help="Remove DNS Exception from tunnel-type client-app")
        deldns_parser.add_argument(dest="exception_fqdn",  metavar='fqdn', nargs="+", help='DNS exception FQDN')
        # Connector attach/detach
        attcon_parser = subsub.add_parser("attach", help="Attach an EAA Connector to the application")
        attcon_parser.add_argument(dest="connector_id", nargs="+",
                                   help='Attach one or multiple connectors to the application e.g. con://123456')
        detcon_parser = subsub.add_parser("detach", help="Detach EAA Connector to the application")
        detcon_parser.add_argument(dest="connector_id", nargs="+",
                                   help='Detach one or multiple connectors to the application, e.g. con://123456.')

        deploy_parser = subsub.add_parser("deploy", help="Deploy the application")
        deploy_parser.add_argument("--comment", "-c", nargs="?", default="Deploy from cli-eaa",
                                   help="Comment for the deployment")
        update_parser = subsub.add_parser("update", help="Update an existing application")
        update_parser.add_argument('--var', dest="variables", action='append', nargs='+')
        create_parser = subsub.add_parser("create", help="Create a new application")
        create_parser.add_argument('--var', dest="variables", default=[], action='append', nargs='+')
        subsub.add_parser("delete", help="Delete an application")
        subsub.add_parser("view", help="Dump application configuration (JSON)")
        subsub.add_parser("viewgroups", help="View groups associated to application")
        subsub.add_parser("delgroup", help="Remove group from application, appgroup ID must provided")
        addgrp_parser = subsub.add_parser("addgroup", help="Add group(s) to application, app ID and appgroup ID must provided")
        addgrp_parser.add_argument(dest="appgrp_id", nargs="+",
                                   help='Add group(s) to application')

        cert_parser = subparsers.add_parser('certificate', aliases=["cert"], help='Manage EAA Certificates')
        cert_parser.add_argument(dest='certificate_id', nargs="?", default=None,
                                 help="Certificate ID (e.g. crt://abcdefghi)")
        subsub = cert_parser.add_subparsers(dest="action", help='Certificate operation')
        subsub.add_parser("list", help="List certificates")
        subsub.add_parser("delete", help="Delete existing certificate")
        subsub.add_parser("status", help="Display status of application/idp using the certificate")
        certadd_parser = subsub.add_parser("rotate", help="Rotate existing certificate with a new one")
        certadd_parser.add_argument('--cert', '-c', required=True, type=argparse.FileType('r'),
                                    help="Certificate in PEM format")
        certadd_parser.add_argument('--key', '-k', required=True, type=argparse.FileType('r'), help="Private Key")
        certadd_parser.add_argument('--passphrase', '--pass', '-p', help="Certificate passphrase")
        certadd_parser.add_argument('--deployafter', '--deploy', '-d', action="store_true", default=False,
                                    help="Deploy impacted apps/idp after the rotation")

        report_parser = subparsers.add_parser('report', aliases=["r"], help='EAA reports')
        report_parser.add_argument(dest='report_name', choices=['clients'], help="Report name")

        con_parser = subparsers.add_parser('connector', aliases=["c", "con"], help='Manage EAA connectors')
        con_parser.add_argument(dest='connector_id', nargs="?", default=None,
                                help="Connector ID (e.g. con://abcdefghi)")
        subsub = con_parser.add_subparsers(dest="action", help="Connector operation")
        app_parser = subsub.add_parser("apps", help="List applications used by the connector")
        app_parser.add_argument('--perf', default=False, action="store_true", help='Show performance metrics')

        list_parser = subsub.add_parser("list", help="List all connectors")
        list_parser.add_argument('--perf', default=False, action="store_true", help='Show performance metrics')
        list_parser.add_argument('--json', '-j', default=False, action="store_true", help='View as JSON')
        list_parser.add_argument('--showapps', '-a', default=False, action="store_true",
                                 help='Response contains the applications running on the connector (JSON only)')
        list_parser.add_argument('--tail', '-f', default=False, action="store_true",
                                 help='Keep watching, do not exit until Control+C/SIGTERM')
        list_parser.add_argument('--interval', '-i', default=300, type=float,
                                 help='Interval between update (works with --tail only)')
        # subparsers.required = False
        swap_parser = subsub.add_parser("swap", help="Swap connector with another one")
        swap_parser.add_argument(dest="new_connector_id", help='New connector ID')
        swap_parser.add_argument('--dryrun', dest="dryrun", action="store_true", default=False, help='Dry run mode')

        subparsers.add_parser('idp', aliases=["i"], help='Manage EAA Identity Providers')

        subparsers.add_parser('info', help='Display tenant info')

        dp_parser = subparsers.add_parser('dp', help='Device Posture')
        dp_parser.add_argument("dpcommand", choices=['inventory'], default="inventory")
        dp_parser.add_argument("--tail", "-f", default=False, action="store_true",
                               help="Keep pulling the inventory every interval seconds")
        dp_parser.add_argument("--interval", "-i", type=int, default=600,
                               help="Pulling interval in seconds (default: 600)")
        # Placeholder future json vs. flat output
        dp_parser.add_argument("--json", "-j", action="store_true", default=True, help=argparse.SUPPRESS)

#        dpdh = subparsers.add_parser('dp_devhist', help='Device Posture Device History (experimental)')
#        $dpdh.add_argument("device_id")

        subparsers.add_parser('version', help='Display cli-eaa module version')

        parser.add_argument('--batch', '-b', default=False, action='store_true',
                            help='Batch mode, remove the extra header/footer in lists.')
        parser.add_argument('--debug', '-d', default=False, action='count', help=' Debug mode (log HTTP headers)')
        parser.add_argument('--edgerc', '-e',
                            default=os.environ.get('AKAMAI_EDGERC', '~/.edgerc'),
                            metavar='credentials_file',
                            help=' Credentials file, [$AKAMAI_EDGERC], then %s)' %
                            os.path.expanduser("~/.edgerc"))
        parser.add_argument('--proxy', '-p', default='', help=''' HTTP/S Proxy Host/IP and port number,
                                                                  do not use prefix (e.g. 10.0.0.1:8888)''')
        parser.add_argument('--section', '-c', default=os.environ.get('AKAMAI_EDGERC_SECTION', 'default'),
                            metavar='credentials_file_section', action='store',
                            help=' Credentials file Section\'s name to use [$AKAMAI_EDGERC_SECTION]')
        parser.add_argument('--accountkey', '--account-key', default=os.environ.get('AKAMAI_EDGERC_ACCOUNT_KEY', None),
                            help=' Account Switch Key [$AKAMAI_EDGERC_ACCOUNT_KEY]')

        parser.add_argument('--verbose', '-v', default=False, action='store_true', help=' Verbose mode')
        parser.add_argument('--logfile', default=None, help=' Log file')
        parser.add_argument('--user-agent-prefix', dest='ua_prefix', default='Akamai-CLI', help=argparse.SUPPRESS)

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
            cli_exit_with_error(rc_error.GENERAL_ERROR)

        arguments = vars(args)

        if "section" in arguments and arguments["section"]:
            configuration = arguments["section"]

        arguments["edgerc"] = os.path.expanduser(arguments["edgerc"])

        if os.path.isfile(arguments["edgerc"]):
            config = ConfigParser()
            config.readfp(open(arguments["edgerc"]))
            if not config.has_section(configuration):
                err_msg = "ERROR: No section named %s was found in your %s file\n" % \
                          (configuration, arguments["edgerc"])
                cli_exit_with_error(rc_error.EDGERC_SECTION_NOT_FOUND, err_msg)

            for key, value in config.items(configuration):
                # ConfigParser lowercases magically
                if key not in arguments or arguments[key] is None:
                    arguments[key] = value
                else:
                    print("Missing configuration file.")
                    print("Run python gen_edgerc.py to get your credentials file set up "
                          "once you've provisioned credentials in Akamai Control Center.")
                    return None
        else:
            err_msg = f"ERROR: EdgeRc configuration {arguments['edgerc']} not found.\n"
            cli_exit_with_error(rc_error.EDGERC_MISSING.value, err_msg)

        for option in arguments:
            setattr(self, option, arguments[option])

        if hasattr(self, 'eaa_api_host'):
            self.create_base_url()

    def create_base_url(self):
        self.base_url = "https://%s" % self.eaa_api_host

# end of file
