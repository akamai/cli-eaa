# Copyright 2021 Akamai Technologies, Inc. All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
from multiprocessing import Pool

from common import cli, BaseAPI, EAAItem
from application import ApplicationAPI


class ConnectorAPI(BaseAPI):
    """
    Handle interactions with EAA Connector API
    """
    POOL_SIZE = 6     # When doing sub request, max concurrency of underlying HTTP request
    LIMIT_SOFT = 256  # Soft limit of maximum of connectors to retreive at once
    NODATA = "-"      # Output value in the CSV cell if data is not available

    def __init__(self, config):
        super(ConnectorAPI, self).__init__(config, api=BaseAPI.API_Version.OpenAPI)

    def exists(self, con_moniker):
        """
        Check if a particular connector exist in the account

        Args:
            con_moniker (EAAItem): Identifier of the connector (e.g. con://123456)

        Returns:
            bool: Existence of the connector
        """
        url_params = {'expand': 'false', 'limit': ConnectorAPI.LIMIT_SOFT}
        data = self.get('mgmt-pop/agents', params=url_params)
        connectors = data.json()
        for c in connectors.get('objects', []):
            if c.get('uuid_url') == con_moniker.uuid:
                return True
        return False

    def perf(self, connector_id):
        """
        Fetch connector performance latest performance data (system and app)

        Args:
            connector_id (str): Connector UUID (not the EAAItem!)

        Returns:
            [tuple]: (connector_id, dictionnary with metric name as key)
        """
        systemres_api_url = 'mgmt-pop/agents/{agentid}/system_resource/metrics'.format(agentid=connector_id)
        perf_data_resp = self.get(systemres_api_url, params={'period': '1h'})
        perf_data = perf_data_resp.json()
        perf_latest = {
            'timestamp': None, 'mem_pct': None, 'disk_pct': None, 'cpu_pct': None,
            'network_traffic_mbps': None, 'dialout_total': None, "dialout_idle": None
        }
        if len(perf_data.get('data', [])) >= 1:
            perf_latest = perf_data.get('data', [])[-1]
        return (connector_id, perf_latest)

    def list(self, perf=False):
        """
        Display the list of EAA connector with a nice comma separated CSV
        """
        url_params = {'expand': 'true', 'limit': ConnectorAPI.LIMIT_SOFT}
        data = self.get('mgmt-pop/agents', params=url_params)
        connectors = data.json()
        total_con = 0
        header = '#Connector-id,name,reachable,status,version,privateip,publicip,debug'
        format_line = "{scheme}{con_id},{name},{reachable},{status},{version},{privateip},{publicip},{debugchan}"
        if perf:
            header += ",CPU%,Mem%,Disk%"
            format_line += ",{ts},{cpu},{mem},{disk}"

        if perf:  # Add performance metrics in the report
            perf_res_list = None
            with Pool(ConnectorAPI.POOL_SIZE) as p:
                perf_res_list = p.map(self.perf, [c.get('uuid_url') for c in connectors.get('objects', [])])
            perf_res = dict(perf_res_list)

        cli.header(header)
        perf_latest = {}
        for total_con, c in enumerate(connectors.get('objects', []), start=1):
            if perf:
                perf_latest = perf_res.get(c.get('uuid_url'), {})
            cli.print(format_line.format(
                scheme=EAAItem.Type.Connector.scheme,
                con_id=c.get('uuid_url'),
                name=c.get('name'),
                reachable=c.get('reach'),
                status=c.get('status'),
                version=c.get('agent_version').replace('AGENT-', '').strip(),
                privateip=c.get('private_ip'),
                publicip=c.get('public_ip'),
                debugchan='Y' if c.get('debug_channel_permitted') else 'N',
                ts=perf_latest.get('timestamp') or ConnectorAPI.NODATA,
                cpu=perf_latest.get('cpu_pct') or ConnectorAPI.NODATA,
                disk=perf_latest.get('disk_pct') or ConnectorAPI.NODATA,
                mem=perf_latest.get('mem_pct') or ConnectorAPI.NODATA
            ))
        cli.footer("Total %s connector(s)" % total_con)

    def findappbyconnector(self, connector_moniker):
        """
        Find EAA Applications using a particular connector.

        Args:
            connector_moniker (EAAItem): Connector ID.

        Raises:
            TypeError: If the argument is wrong type.
        """
        if not isinstance(connector_moniker, EAAItem):
            raise TypeError("EAAItem expected.")
        url_params = {'limit': ApplicationAPI.LIMIT_SOFT, 'expand': 'true'}
        search_app = self.get('mgmt-pop/apps', params=url_params)
        apps = search_app.json()
        cli.print("Searching app using %s..." % connector_moniker)
        for app in apps.get('objects', []):
            for con in app.get('agents', []):
                app_moniker = EAAItem("app://" + app.get('uuid_url'))
                con_moniker = EAAItem("con://" + con.get('uuid_url'))
                if con_moniker == connector_moniker:
                    yield app_moniker

        #    if a.get('cert') == certid:
        #        yield (EAAItem("app://%s" % a.get('uuid_url')), a.get('name'))

    def swap(self, old_con_id, new_con_id, dryrun=False):
        """
        Replace an EAA connector with another in:
        - application
        - directory

        Args:
            old_con_id (EAAItem): Existing connector to be replaced
            new_con_id (EAAItem): New connector to attach on the applications and directories
            dryrun (bool, optional): Enable dry run. Defaults to False.
        """
        old_con = EAAItem(old_con_id)
        new_con = EAAItem(new_con_id)
        cli.print("Swapping connector %s with connector %s..." % (old_con_id, new_con_id))
        if not self.exists(new_con):
            cli.print_error("EAA connector %s not found." % new_con)
            cli.print_error("Please check with command 'akamai eaa connector'.")
            cli.exit(2)
        # app_api = ApplicationAPI(self._config)
        for app_using_old_con in self.findappbyconnector(old_con):
            if dryrun:
                cli.print("DRYRUN: Adding %s in %s" % (new_con, app_using_old_con))
                cli.print("DRYRUN: Removing %s in %s" % (old_con, app_using_old_con))
            else:
                cli.print("To be implemented")
