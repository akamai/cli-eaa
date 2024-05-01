# Copyright 2024 Akamai Technologies, Inc. All Rights Reserved
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
import datetime
from functools import lru_cache
import io
import csv
from dateutil.parser import parse
import pytz
from enum import Enum

from common import cli, BaseAPI, EAAItem
from application import ApplicationAPI


class ConnectorAPI(BaseAPI):
    """
    Handle interactions with EAA Connector API
    """
    POOL_SIZE = 6        # When doing sub request, max concurrency of underlying HTTP request
    LIMIT_SOFT = 1024    # Soft limit of maximum of connectors to retreive at once
    APP_CACHE_TTL = 300  # How long we consider the app <-> connector mapping accurate enough
    NODATA = "-"         # Output value in the CSV cell if data is not available
    NODATA_JSON = None   # Output value in the JSON cell if data is not available

    class ConnectorPackage(Enum):
        VMWare = 1
        VirtualBox = 2
        AWS = 3
        KVM = 4
        HyperV = 5
        Docker = 6
        AWS_Classic = 7
        Azure = 8
        Google = 9
        Softlayer = 10
        Fujitsu = 11

    def __init__(self, config):
        super(ConnectorAPI, self).__init__(config, api=BaseAPI.API_Version.OpenAPI)

    def load(self, con_moniker: EAAItem):
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
        except Exception:
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

    def list_once(self, perf=False, json_fmt=False, show_apps=False):
        """
        Display the list of EAA connectors as comma separated CSV or JSON
        TODO: refactor this method, too long
        """
        url_params = {'expand': 'true', 'limit': ConnectorAPI.LIMIT_SOFT}
        data = self.get('mgmt-pop/agents', params=url_params)
        if data.status_code != 200:
            cli.print_error(f"API Error HTTP/{data.status_code} for {data.url}")
            cli.exit(2)

        dt = datetime.datetime.now(tz=datetime.timezone.utc)
        connectors = data.json()
        total_con = 0
        header = '#Connector-id,name,reachable,status,version,privateip,publicip,debug'
        format_line = "{scheme}{con_id},{name},{reachable},{status},{version},{privateip},{publicip},{debugchan}"
        if perf:
            header += ",last_upd,CPU%,Mem%,Disk%,NetworkMbps,do_total,do_idle,do_active"
            format_line += ",{ts},{cpu},{mem},{disk},{network},{dialout_total},{dialout_idle},{dialout_active}"
            # Add performance metrics in the report
            perf_res_list = None
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
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
                "debugchan": 'Y' if c.get('debug_channel_permitted') else 'N',
                "os_version": c.get('os_version') or ConnectorAPI.NODATA_JSON,
                "datetime": dt.isoformat()
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
            # Help SIEM with the mapping connector <-> apps
            if show_apps:
                apps = []
                for a in self.findappbyconnector(EAAItem("con://" + c.get('uuid_url'))):
                    apps.append(str(a[2]))
                data.update({"apps": apps})
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

    def list(self, perf, json_fmt, show_apps=False, follow=False, interval=300, stop_event=None):
        """
        List the connector and their attributes and status
        The default output is CSV

        Args:
            perf (bool):        Add performance data (cpu, mem, disk, dialout)
            json_fmt (bool):    Output as JSON instead of CSV
            show_apps (bool):   Add an extra field 'apps' as array of application UUID
            follow (bool):      Never stop until Control+C or SIGTERM is received
            interval (float):   Interval in seconds between pulling the API, default is 5 minutes (300s)
            stop_event (Event): Main program stop event allowing the function
                                to stop at the earliest possible
        """
        while True or (stop_event and not stop_event.is_set()):
            try:
                start = time.time()
                self.list_once(perf, json_fmt, show_apps)
                if follow:
                    sleep_time = interval - (time.time() - start)
                    if sleep_time > 0:
                        stop_event.wait(sleep_time)
                    else:
                        logging.error(f"The EAA Connector API is slow to respond (could be also a proxy in the middle)"
                                      f" holding for {interval} sec.")
                        stop_event.wait(interval)
                else:
                    break
            except Exception as e:
                if follow:
                    logging.error(f"General exception {e}, since we are in follow mode (--tail), we keep going.")
                else:
                    raise

    @lru_cache(maxsize=1)
    def all_apps(self, exp):
        """
        This method is expensive in time so we use `lru_cache decorator`
        with a size of 1, combined with a functiom argument `exp` that will be
        used as expiration or cache key.

        Args:
            exp (integer): cache key
        Returns:
            [dict]: JSON dictionnary containing all the applications for this tenant
        """
        url_params = {'limit': ApplicationAPI.LIMIT_SOFT, 'expand': 'true'}
        search_app = self.get('mgmt-pop/apps', params=url_params)
        return search_app.json()

    def allow_list(self):
        """
        Print the Connector Allow List of endpoint (IP/CIDR or host)
        as a CSV output.
        """
        appcount_by_cloudzone = {}
        later_than = None
        if self._config.since_time:
            later_than = parse(self._config.since_time)
            if not later_than.tzname():
                later_than = pytz.utc.localize(later_than)

        if self._config.only_used:
            app_factory = ApplicationAPI(self._config, BaseAPI.API_Version.OpenAPIv3)
            appcount_by_cloudzone = app_factory.stats_by_cloudzone()

        csv_output = io.StringIO()
        ep_fmt = "IP/CIDR"
        if self._config.fqdn:
            ep_fmt = "FQDN"

        csv_writer = csv.writer(csv_output, quoting=csv.QUOTE_MINIMAL)
        if not self._config.skip_header:
            fieldnames = ['Service', 'Location', 'Protocol', ep_fmt, 'LastUpdate', 'Apps']
            csv_writer.writerow(fieldnames)
        r = self.get("zt/outboundallowlist")
        for l in r.json():
            d = datetime.datetime.fromisoformat(l.get('modifiedDate'))
            used_apps = appcount_by_cloudzone.get(l.get('location'))
            if later_than and d < later_than:
                continue
            if self._config.fqdn:
                hosts = l.get('host').split(",")
                gen = (h for h in hosts if h not in ('-', ))
                for h in gen:
                    csv_writer.writerow([l.get('service'), l.get('location'), l.get('protocol'), h.strip(), l.get('modifiedDate'), used_apps])
            else:
                for ip in l.get('ips', []):
                    csv_writer.writerow([l.get('service'), l.get('location'), l.get('protocol'), ip.get('ip'), ip.get('modifiedDate'), used_apps])

        cli.print(csv_output.getvalue())

    def findappbyconnector(self, connector_moniker):
        """
        Find EAA Applications using a particular connector.

        Args:
            connector_moniker (EAAItem): Connector ID.

        Returns:
            Tuple of 4 values:
                - application moniker
                - application name
                - application host (external hostname - FQDN)
                - dialout version (1 or 2)

        Raises:
            TypeError: If the argument is wrong type.
        """

        if not isinstance(connector_moniker, EAAItem):
            raise TypeError("EAAItem expected.")

        now = time.time()
        exp = now - now % (-1 * ConnectorAPI.APP_CACHE_TTL)
        apps = self.all_apps(exp)

        logging.debug("Searching app using %s..." % connector_moniker)
        for app in apps.get('objects', []):
            # Only tunnel apps are using Dialout Version 2
            dialout_ver = 2 if app.get('app_profile') == ApplicationAPI.Profile.TCP.value else 1
            for con in app.get('agents', []):
                app_moniker = EAAItem("app://" + app.get('uuid_url'))
                con_moniker = EAAItem("con://" + con.get('uuid_url'))
                app_host = app.get('host')
                if app.get('domain') == 2:
                    app_host += "." + app.get('domain_suffix')
                if con_moniker == connector_moniker:
                    yield app_moniker, \
                          app.get('name'), \
                          app_host, \
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
        for app_using_old_con, app_name, app_host, do_ver in self.findappbyconnector(old_con):
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


    def create(self, config):

        if config.connector_package not in ConnectorAPI.ConnectorPackage._member_names_:
            cli.print_error(f"Invalid Connector Package {config.connector_package}.")
            cli.print_error(f"Options are: {", ".join(ConnectorAPI.ConnectorPackage._member_names_)}")
            cli.exit(2)

        connector_package_lookup = {member.name: member.value for member in ConnectorAPI.ConnectorPackage}

        payload = {
            "name": config.connector_name,
            "description": config.connector_description,
            # "status": 1,
            "debug_channel_permitted": config.connector_debug,
            "package": connector_package_lookup.get(config.connector_package)
        }

        response = self.post('mgmt-pop/agents', json=payload)
        if response.status_code != 200:
            cli.print_error(f"Connector was not created due to the following error: {response.text}")
            cli.exit(2)

        connector_info = response.json()
        connector_moniker = EAAItem(f"con://{connector_info.get("uuid_url")}")
        start = time.time()
        wait_until = start + config.connector_dl_wait
        wait_interval = 1  # Start interval in seconds
        bakeoff_factor = 2 # Multiplier of wait time between each poll
        bakeoff_max = 60 # max interval we wait between each poll
        while time.time() < wait_until:
            connector_info = self.load(connector_moniker)
            if connector_info.get('download_url'):
                break
            logging.debug(f"Wait {wait_interval}s...")
            time.sleep(wait_interval)
            wait_interval = min(wait_interval * bakeoff_factor, bakeoff_max)

        cli.print(json.dumps(connector_info, indent=2))

    def remove(self, connector_moniker: EAAItem):
        "Delete an EAA connector."
        r = self.delete(f'mgmt-pop/agents/{connector_moniker.uuid}')
        if r.status_code == 204:
            cli.print("Connector deleted successfully.")
            return_code = 0
        else:
            cli.print_error(f"Can't delete connector {connector_moniker.uuid}, API returned HTTP/{r.status_code}.")
            cli.print_error("Use: akamai eaa connector list")
            return_code = 1
        cli.exit(return_code)
