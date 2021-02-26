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

    def load(self, con_moniker):
        """
        Load a connector config

        Args:
            con_moniker (EAAItem): Connector identifier (e.g. con://123456)

        Returns:
            bool/dict: False if connector doesn't exist
                       The full dictionnary configuration of the connector if found
        """
        url_params = {'expand': 'false', 'limit': ConnectorAPI.LIMIT_SOFT}
        data = self.get('mgmt-pop/agents', params=url_params)
        connectors = data.json()
        for c in connectors.get('objects', []):
            if c.get('uuid_url') == con_moniker.uuid:
                return c
        return False

    def perf_system(self, connector_id):
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

    def perf_apps(self, connector_id):
        """
        Fetch app usage for a connector

        Args:
            connector_id ([type]): [description]
        """
        perfapp_api_url = 'mgmt-pop/agents/{agentid}/apps_resource/metrics'.format(agentid=connector_id)
        perf_data_resp = self.get(perfapp_api_url, params={'period': '1h', 'filter_all': 'false'})
        perf_by_host = {}
        if perf_data_resp.status_code == 200:
            for perf_by_app in perf_data_resp.json().get('data', []):
                perf_by_host[perf_by_app.get('app_name')] = {}
                if len(perf_by_app.get('histogram_data', [])[-1]) >= 1:
                    perf_by_host[perf_by_app.get('app_name')] = perf_by_app.get('histogram_data')[-1]
        return perf_by_host

    def list(self, perf=False):
        """
        Display the list of EAA connectors as comma separated CSV
        """
        url_params = {'expand': 'true', 'limit': ConnectorAPI.LIMIT_SOFT}
        data = self.get('mgmt-pop/agents', params=url_params)
        connectors = data.json()
        total_con = 0
        header = '#Connector-id,name,reachable,status,version,privateip,publicip,debug'
        format_line = "{scheme}{con_id},{name},{reachable},{status},{version},{privateip},{publicip},{debugchan}"
        if perf:
            header += ",last_upd,CPU%,Mem%,Disk%,NetworkMbps,do_total,do_idle,do_active"
            format_line += ",{ts},{cpu},{mem},{disk},{network},{dialout_total},{dialout_idle},{dialout_active}"

        if perf:  # Add performance metrics in the report
            perf_res_list = None
            with Pool(ConnectorAPI.POOL_SIZE) as p:
                perf_res_list = p.map(self.perf_system, [c.get('uuid_url') for c in connectors.get('objects', [])])
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
                version=((c.get('agent_version') or ConnectorAPI.NODATA)).replace('AGENT-', '').strip(),
                privateip=c.get('private_ip') or ConnectorAPI.NODATA,
                publicip=c.get('public_ip') or ConnectorAPI.NODATA,
                debugchan='Y' if c.get('debug_channel_permitted') else 'N',
                ts=perf_latest.get('timestamp') or ConnectorAPI.NODATA,
                cpu=perf_latest.get('cpu_pct') or ConnectorAPI.NODATA,
                disk=perf_latest.get('disk_pct') or ConnectorAPI.NODATA,
                mem=perf_latest.get('mem_pct') or ConnectorAPI.NODATA,
                network=perf_latest.get('network_traffic_mbps') or ConnectorAPI.NODATA,
                dialout_total=perf_latest.get('dialout_total') or ConnectorAPI.NODATA,
                dialout_idle=perf_latest.get('dialout_idle') or ConnectorAPI.NODATA,
                dialout_active=perf_latest.get('dialout_active') or ConnectorAPI.NODATA
            ))
        cli.footer("Total %s connector(s)" % total_con)

    def findappbyconnector(self, connector_moniker):
        """
        Find EAA Applications using a particular connector.

        Args:
            connector_moniker (EAAItem): Connector ID.

        Returns:
            Tuple of 3 values:
                - application moniker
                - application name
                - application host (external hostname)

        Raises:
            TypeError: If the argument is wrong type.
        """
        if not isinstance(connector_moniker, EAAItem):
            raise TypeError("EAAItem expected.")
        url_params = {'limit': ApplicationAPI.LIMIT_SOFT, 'expand': 'true'}
        search_app = self.get('mgmt-pop/apps', params=url_params)
        apps = search_app.json()
        logging.debug("Searching app using %s..." % connector_moniker)
        for app in apps.get('objects', []):
            for con in app.get('agents', []):
                app_moniker = EAAItem("app://" + app.get('uuid_url'))
                con_moniker = EAAItem("con://" + con.get('uuid_url'))
                if con_moniker == connector_moniker:
                    yield app_moniker, app.get('name'), app.get('host')

    def list_apps(self, con_moniker, perf=False):
        if not isinstance(con_moniker, EAAItem):
            raise TypeError("con_moniker")
        if perf:
            perf_by_apphost = self.perf_apps(con_moniker.uuid)
            line_fmt = "{app_id},{app_name},{perf_upd},{active}"
            cli.header("#app_id,app_name,perf_upd,active")
        else:
            line_fmt = "{app_id},{app_name}"
            cli.header("#app_id,app_name")
        for c, (app_id, app_name, app_host) in enumerate(self.findappbyconnector(con_moniker), start=1):
            perf_data = {}
            if perf:
                perf_data = perf_by_apphost.get(app_host, {})
            cli.print(line_fmt.format(
                app_id=app_id,
                app_name=app_name,
                perf_upd=perf_data.get('timestamp', ConnectorAPI.NODATA),
                active=perf_data.get('active', ConnectorAPI.NODATA)
            ))
        cli.footer("%s application(s) attached to connector %s" % (c, con_moniker.uuid))

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
        infos_by_conid = {}
        old_con = EAAItem(old_con_id)
        new_con = EAAItem(new_con_id)
        for c in [old_con, new_con]:
            connector_info = self.load(c)
            if not connector_info:
                cli.print_error("EAA connector %s not found." % c)
                cli.print_error("Please check with command 'akamai eaa connector'.")
                cli.exit(2)
            # Save the details for better
            infos_by_conid[c] = connector_info
        app_api = ApplicationAPI(self._config)
        app_processed = 0
        cli.header("#Operation,connector-id,connector-name,app-id,app-name")
        for app_using_old_con, app_name, app_host in self.findappbyconnector(old_con):
            if dryrun:
                cli.print("DRYRUN +,%s,%s,%s,%s" % (
                    new_con, infos_by_conid[new_con].get('name'),
                    app_using_old_con, app_name))
                cli.print("DRYRUN -,%s,%s,%s,%s" % (
                    old_con, infos_by_conid[old_con].get('name'),
                    app_using_old_con, app_name))
            else:
                app_api.attach_connectors(app_using_old_con, [{'uuid_url': new_con.uuid}])
                cli.print("+,%s,%s,%s,%s" % (
                    new_con, infos_by_conid[new_con].get('name'),
                    app_using_old_con, app_name))
                app_api.detach_connectors(app_using_old_con, [{'uuid_url': old_con.uuid}])
                cli.print("-,%s,%s,%s,%s" % (
                    old_con, infos_by_conid[old_con].get('name'),
                    app_using_old_con, app_name))
            app_processed += 1
        if app_processed == 0:
            cli.footer("Connector %s is not used by any application." % old_con_id)
            cli.footer("Check with command 'akamai eaa connector %s apps'" % old_con_id)
        else:
            cli.footer("Connector swapped in %s application(s)." % app_processed)
            cli.footer("Updated application(s) is/are marked as ready to deploy")
