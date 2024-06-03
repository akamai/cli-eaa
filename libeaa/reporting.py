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
import time
import json
from urllib.parse import parse_qsl
import datetime
import csv
import sys

# cli-eaa
from common import cli, BaseAPI
from application import ApplicationAPI
from idp import IdentityProviderAPI

logger = logging.getLogger(__name__)

class ReportingAPI(BaseAPI):

    LIMIT_ACCESS_REPORT = 5000  #: API limit, 5000 is the max

    def __init__(self, config):
        super(ReportingAPI, self).__init__(config, api=BaseAPI.API_Version.OpenAPI)

    def clients(self):
        now = time.time()
        params = {
            'limit': 0,
            'start': int((now - 30 * 24 * 60 * 60) * 1000),
            'end': int(now * 1000)
        }
        resp = self.get('mgmt-pop/clients', params=params)
        if resp.status_code != 200:
            logger.error(resp.text)
        data = resp.json()
        cli.header("#device_id,version,idp_user,idp_host,lastseen")
        for count, c in enumerate(data.get('objects', {})):
            cli.print("{device_id},{version},{idp_user},{idp_host},{lastseen}".format(
                device_id=c.get("device_id"),
                version=c.get("device_info", {}).get("version"),
                idp_user=c.get("idp_user"),
                idp_host=c.get("idp_host"),
                lastseen=c.get("timestamp")
            ))
        cli.footer("%s unique EAA Clients checked-in in the last 30 days" % count)


    @staticmethod
    def facility_from_popname(pop_name):
        """
        Crudly derive the facility based on the POP name.
        """
        facility = "AWS"
        if "-LIN-" in pop_name:
            facility = "Akamai Cloud Compute (formerly Linode)"
        return facility

    def tenant_info(self):
        """
        Display tenant info/stats.
        """
        info = {"cloudzones": []}
        resp = self.get('mgmt-pop/pops?shared=true')

        if self._config.show_usage:
            app_apiv3 = ApplicationAPI(self._config, BaseAPI.API_Version.OpenAPIv3)
            app_api = ApplicationAPI(self._config, BaseAPI.API_Version.OpenAPI)
            idp_api = IdentityProviderAPI(self._config)
            app_by_cz = app_apiv3.stats_by_cloudzone()
            entdns_by_cz = app_api.entdns_stats_by_cloudzone()
            idp_by_pop = idp_api.stats_by_pop()

        scanned_cz = []
        for eaa_cloudzone in resp.json().get('objects'):
            cz_info = {
                "name": eaa_cloudzone.get('region'),
                "facility": ReportingAPI.facility_from_popname(eaa_cloudzone.get('name')),
            }
            if self._config.show_usage:
                cz_info["count_idp"] = idp_by_pop.get(eaa_cloudzone.get('uuid_url'), 0)
                cz_info["count_app"] = app_by_cz.get(eaa_cloudzone.get('region'), 0)
                cz_info["count_entdns"] = entdns_by_cz.get(eaa_cloudzone.get('region'), 0)

            scanned_cz.append(cz_info)

        # sort by Cloud Zone name
        info['cloudzones'] = sorted(scanned_cz, key=lambda x: x['name'])

        cli.print(json.dumps(info, indent=4))

    def deviceposture_inventory(self, follow=False, interval=300):
        """
        Fetch Device Posture inventory once or until a SIG_TERM is received or Control-C is pressed

        Args:
            follow (bool, optional): Will not terminate and keep pulling every `interval` sec. Defaults to False.
            interval (int, optional): Interval in seconds to pull the inventory. Defaults to 300.
        """
        while not cli.stop_event.is_set():
            start = time.time()
            offset = 0
            limit = 3000
            devices = []

            while not cli.stop_event.is_set():
                page_start = time.time()
                resp = self.get('device-posture/inventory/list', params={'offset': offset, 'limit': limit})
                if resp.status_code != 200:
                    cli.print_error("Non HTTP 200 response fromt the API")
                    cli.exit(2)
                doc = resp.json()
                meta = doc.get('meta', {})
                next_page = meta.get('next')
                limit = meta.get('limit')
                objects_in_page = doc.get('objects', [])
                offset = dict(parse_qsl(next_page)).get('offset')
                logger.debug("--- DP Inventory page with {c} devices fetched in {elapsed:.2f} seconds".format(
                              c=len(objects_in_page), elapsed=time.time()-page_start))
                devices += objects_in_page
                if not next_page:
                    break

            for d in devices:
                cli.print(json.dumps(d))

            logger.debug("DP Inventory Total {device_count} devices fetched in {elapsed:.2f} seconds".format(
                          device_count=len(devices), elapsed=time.time()-start))
            if follow is False:
                break
            else:
                wait_time = interval - (time.time() - start)  # interval - time elapsed
                if wait_time > 0:
                    logger.debug("Sleeping for {:.2f} seconds".format(wait_time))
                    time.sleep(wait_time)
                else:
                    logger.warn("Fetching data takes more time than the interval, "
                                 "consider increase the --interval parameter")

    def deviceposture_devicehistory(self, device_id):
        resp = self.get('device-posture/inventory/device-history/{deviceId}'.format(deviceId=device_id))
        cli.print(json.dumps(resp.json(), indent=4))

    def last_access(self, start: int, end: int, app: str = None):
        """
        Report with unique user ID and last access to the given application
        Application can be a business application on an IdP
        """
        params = {
            "start": start * 1000,
            "end": end * 1000,
            "tz": "UTC",
            "limit": 50,
        }
        params["start"] = 1717052400000
        params["end"] = 1717202781000
        # params["_remove-extras_"] = 1
        if app:
            params["app"] = app
        # params
        resp = self.get('application-reports/ops/query', params=params)
        cli.print(json.dumps(resp.json(), indent=4))


    @staticmethod
    def split_time_range(start, end, num_sub_ranges):
        if num_sub_ranges <= 0:
            raise ValueError("Number of sub-ranges must be greater than zero")
        if start >= end:
            raise ValueError("End time must be greater than start time")

        total_duration = end - start
        sub_range_duration = total_duration // num_sub_ranges
        remainder = total_duration % num_sub_ranges

        sub_ranges = []
        current_start = start

        for i in range(num_sub_ranges):
            current_end = current_start + sub_range_duration
            if remainder > 0:
                current_end += 1
                remainder -= 1
            sub_ranges.append((current_start, current_end))
            current_start = current_end

        return sub_ranges

    def _last_access(self, start: int, end: int, app: str = None):
        logger.debug(f"_last_access() | start={start} end={end} ({end-start}s) app={app}")
        params = {
            "start": start * 1000,
            "end": end * 1000,
            "tz": "UTC",
            "limit": ReportingAPI.LIMIT_ACCESS_REPORT
        }
        if app:
            params["app"] = app
        # params
        resp = self.get('mgmt-pop/application-reports/ops/query', params=params)
        if resp.status_code != 200:
            cli.print_error("Unexpected response {resp.url}: HTTP/{resp.status_code}")
            cli.exit(2)

        data = resp.json().get('data', [])
        logger.debug(f"_last_access() | {len(data)} records | API time {resp.elapsed.total_seconds():.2f} sec")
        return data

    def last_access(self, start: int, end: int, app: str = None):
        """
        Report with unique user ID and last access to the given application
        Application can be a business application on an IdP
        """
        split_factor = 2
        num_sub_ranges = 1
        api_calls = 0
        records = []
        split_scan = True
        progress_start = start

        while split_scan:
            logger.debug(f"last_access() | Querying API using {num_sub_ranges} interval(s)...")
            ranges = ReportingAPI.split_time_range(progress_start, end, num_sub_ranges)
            for index_range, r in enumerate(ranges):
                logger.info(f"last_access() | ### {len(records):,} records so far. Fetching range {index_range+1} of {num_sub_ranges}...")
                sub_records = self._last_access(r[0], r[1], app)
                api_calls += 1
                if len(sub_records) < ReportingAPI.LIMIT_ACCESS_REPORT: # We got the right level of subsplitting, carry on
                    records.extend(sub_records)
                    if r[1] < end: progress_start = r[1] # if we ever have to subsplit, we don't need to redo it for everything
                    if len(sub_records) < (ReportingAPI.LIMIT_ACCESS_REPORT // split_factor) and r[1] < end:
                        logger.debug("last_access() | Very little data returned, let's oversplit...")
                        num_sub_ranges = num_sub_ranges // split_factor
                        split_scan = True
                        break # Triggers a new for loop with new intervals
                    else:
                        split_scan = False # We continue the for loop normally
                else:
                    # There is likely more data
                    # We need smaller sub range
                    num_sub_ranges = num_sub_ranges * split_factor
                    logger.debug(f"last_access() | Restarting with smaller time range, dividing by {num_sub_ranges}...")
                    split_scan = True
                    break

        # end while, we should have all the data now.

        processed_records = 0
        last_access_by_user = {}
        for access in records:
            processed_records += 1
            scanned_user = access.get('uid')
            scanned_access_time = access.get('ts')
            if scanned_user in last_access_by_user:
                if scanned_access_time > last_access_by_user[scanned_user]:
                    last_access_by_user[scanned_user] = scanned_access_time
            else:
                last_access_by_user[scanned_user] = scanned_access_time


        total_users = 0

        csv_header = ["userid", "last_access_epoch_ms", "last_access_iso8601"]
        csv_rows = []
        for u in sorted(last_access_by_user):
            dt = datetime.datetime.fromtimestamp(last_access_by_user[u]/1000, tz=datetime.timezone.utc)
            iso8601_string = dt.isoformat() + "Z"
            csv_rows.append([u, last_access_by_user[u], iso8601_string])
            total_users += 1
        csv_writer = csv.writer(sys.stdout)
        csv_writer.writerow(csv_header)
        csv_writer.writerows(csv_rows)

        cli.footer(f"Range start: {start} {datetime.datetime.fromtimestamp(start)}")
        cli.footer(f"Range end: {end} {datetime.datetime.fromtimestamp(end)}")
        cli.footer(f"{total_users} users accessed the application for this time range, {processed_records} records processed")
        cli.footer(f"{api_calls} API calls issued.")

