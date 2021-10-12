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

import logging
from multiprocessing import Pool
import time
import json
import signal

from common import cli, BaseAPI, EAAItem
from application import ApplicationAPI


class ConnectorAPI(BaseAPI):
    """
    Handle interactions with EAA Connector API
    """
    POOL_SIZE = 6        # When doing sub request, max concurrency of underlying HTTP request
    LIMIT_SOFT = 256     # Soft limit of maximum of connectors to retreive at once
    NODATA = "-"         # Output value in the CSV cell if data is not available
    NODATA_JSON = None   # Output value in the CSV cell if data is not available

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
        try:  # This method is executed as separate thread, we need the able to troubleshoot
            systemres_api_url = 'mgmt-pop/agents/{agentid}/system_resource/metrics'.format(agentid=connector_id)
            perf_data_resp = self.get(systemres_api_url, params={'period': '1h'})
            perf_data = perf_data_resp.json()
            perf_latest = {
                'timestamp': None, 
                'mem_pct': None, 'disk_pct': None, 'cpu_pct': None,
                'network_traffic_mbps': None, 
                'dialout_total': None, 'dialout_idle': None, 'active_dialout_count': None
            }
            if len(perf_data.get('data', [])) >= 1:
                perf_latest = perf_data.get('data', [])[-1]
            return (connector_id, perf_latest)
        except:
            logging.exception("Error during fetching connector performance health.")

    def perf_apps(self, connector_id):
        """
        Fetch app usage for a connector

        Args:
            connector_id (string): Connector UUID without prefix
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

    def list_once(self, perf=False, json_fmt=False):
        """
        Display the list of EAA connectors as comma separated CSV or JSON
        TODO: refactor this method, too long
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
            signal.signal(signal.SIGTERM, cli.proc_noop)
            with Pool(ConnectorAPI.POOL_SIZE) as p:
                perf_res_list = p.map(self.perf_system, [c.get('uuid_url') for c in connectors.get('objects', [])])
            perf_res = dict(perf_res_list)
            signal.signal(signal.SIGTERM, cli.exit_gracefully)

        if not json_fmt:
            cli.header(header)
        perf_latest = {}
        for total_con, c in enumerate(connectors.get('objects', []), start=1):
            if perf:
                perf_latest = perf_res.get(c.get('uuid_url'), {})

            agent_version = c.get('agent_version') or ConnectorAPI.NODATA_JSON
            if agent_version:
                agent_version = agent_version.replace('AGENT-', '').strip()

            data = {
                "connector_uuid": c.get('uuid_url'),
                "name": c.get('name'),
                "reachable": c.get('reach'),
                "status": c.get('status'),
                "version": agent_version,
                "privateip": c.get('private_ip') or ConnectorAPI.NODATA_JSON,
                "publicip": c.get('public_ip') or ConnectorAPI.NODATA_JSON,
                "debugchan": 'Y' if c.get('debug_channel_permitted') else 'N'
            }
            if perf:
                data.update({
                    "ts": perf_latest.get('timestamp') or ConnectorAPI.NODATA_JSON,
                    "cpu": perf_latest.get('cpu_pct') or ConnectorAPI.NODATA_JSON,
                    "disk": perf_latest.get('disk_pct') or ConnectorAPI.NODATA_JSON,
                    "mem": perf_latest.get('mem_pct') or ConnectorAPI.NODATA_JSON,
                    "network": perf_latest.get('network_traffic_mbps') or ConnectorAPI.NODATA_JSON,
                    "dialout_total": perf_latest.get('dialout_total') or ConnectorAPI.NODATA_JSON,
                    "dialout_idle": perf_latest.get('dialout_idle') or ConnectorAPI.NODATA_JSON,
                    "dialout_active": perf_latest.get('active_dialout_count') or ConnectorAPI.NODATA_JSON
                })
            if not json_fmt:
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
                    dialout_active=perf_latest.get('active_dialout_count') or ConnectorAPI.NODATA
                ))
            else:
                cli.print(json.dumps(data))
        if not json_fmt:
            cli.footer("Total %s connector(s)" % total_con)

    def list(self, perf, json_fmt, follow=False, interval=300, stop_event=None):
        """
        List the connector and their attributes and status
        The default output is CSV

        Args:
            perf (bool):        Add performance data (cpu, mem, disk, dialout)
            json_fmt (bool):    Output as JSON instead of CSV
            follow (bool):      Never stop until Control+C or SIGTERM is received
            interval (float):   Interval in seconds between pulling the API, default is 5 minutes (300s)
            stop_event (Event): Main program stop event allowing the function
                                to stop at the earliest possible
        """
        while True or (stop_event and not stop_event.is_set()):
            try:
                start = time.time()
                self.list_once(perf, json_fmt)
                if follow:
                    sleep_time = interval - (time.time() - start)

                    if sleep_time > 0:
                        # [MS] switching to event sleep (mirroring behavior on regular log output)
                        #time.sleep(sleep_time)
                        stop_event.wait(sleep_time)
                    else:
                        logging.error(f"The EAA Connector API is slow to respond (could be also a proxy in the middle), holding for {interval} sec.")
                        # [MS] switching to event sleep (mirroring behavior on regular log output)
                        #time.sleep(interval)
                        stop_event.wait(sleep_time)
                else:
                    break
            except Exception as e:
                if follow:
                    logging.error(f"General exception {e}, since we are in follow mode (--tail), we keep going.")
                else:
                    raise

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
                - dialout version (1 or 2)

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
            # Only tunnel apps are using Dialout Version 2
            dialout_ver = 2 if app.get('app_profile') == ApplicationAPI.Profile.TCP.value else 1
            for con in app.get('agents', []):
                app_moniker = EAAItem("app://" + app.get('uuid_url'))
                con_moniker = EAAItem("con://" + con.get('uuid_url'))
                if con_moniker == connector_moniker:
                    yield app_moniker, \
                          app.get('name'), \
                          app.get('host'), \
                          dialout_ver

    def list_apps(self, con_moniker, perf=False):
        """
        List applications attached to the connector

        Args:
            con_moniker (EAAItem): Connector UUID moniker
            perf (bool, optional): Display performance metrics. Defaults to False.

        Raises:
            TypeError: If moniker type is not EAAItem
        """
        if not isinstance(con_moniker, EAAItem):
            raise TypeError("con_moniker")
        if perf:
            perf_by_apphost = self.perf_apps(con_moniker.uuid)
            line_fmt = "{app_id},{app_name},{do_ver},{perf_upd},{active}"
            cli.header("#app_id,app_name,do_ver,perf_upd,active")
        else:
            line_fmt = "{app_id},{app_name},{do_ver}"
            cli.header("#app_id,app_name,do_ver")
        for c, (app_id, app_name, app_host, do_ver) in enumerate(self.findappbyconnector(con_moniker), start=1):
            perf_data = {}
            if perf:
                perf_data = perf_by_apphost.get(app_host, {})
            cli.print(line_fmt.format(
                app_id=app_id,
                app_name=app_name,
                do_ver=do_ver,
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
