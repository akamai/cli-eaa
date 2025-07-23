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

# Python core modules
import sys
from enum import Enum
import logging
import datetime
import time
import signal
import os
import json
import re

# 3rd party modules
import requests

# cli-eaa modules
import common
from common import config, cli, CLIFatalException

#: Source string for the Access/Admin Events API server
SOURCE = 'akamai-cli/eaa'

#: Expected Response Content Type from SIEM Log API
RESPONSE_CONTENTTYPE = "application/json"

logger = logging.getLogger(__name__)


def isDigit(x):
    try:
        float(x)
        return True
    except ValueError:
        return False


class EventLogAPI(common.BaseAPI):
    """
    EAA logs, this is using the legacy EAA API
    Inspired by EAA Splunk app
    """

    #: Pull interval when using the tail mode
    PULL_INTERVAL_SEC = 15
    #: Pull delay mininum
    COLLECTION_MIN_DELAY_SEC = 60

    class EventType(Enum):
        USER_ACCESS = "access"
        ADMIN = "admin"

    ADMINEVENT_API = "adminevents-reports/ops/splunk-query"
    ACCESSLOG_API = "analytics/ops"
    ACCESSLOG_API_V2 = "analytics/ops-data"

    def __init__(self, config):
        if (
            hasattr(config, "eaa_api_key") and
            hasattr(config, "eaa_api_secret")
        ):
            super(EventLogAPI, self).__init__(config, api=common.BaseAPI.API_Version.Legacy)
        else:
            super(EventLogAPI, self).__init__(config, api=common.BaseAPI.API_Version.OpenAPI)
        self._content_type_json = {'content-type': 'application/json'}
        self._content_type_form = {'content-type': 'application/x-www-form-urlencoded'}
        self._headers = None
        self._output = config.output
        if not self._output:
            self._output = sys.stdout
        self.line_count = 0
        self.error_count = 0

    def userlog_prepjson(d):
        """
        By default all fields are extracted as string even if they are integer or float.
        This straights up the type to optimize the JSON ouput.
        """
        int_fields = ['req_size', 'status_code', 'bytes_out', 'bytes_in', 'con_srcport', 'error_code']
        float_fields = ['total_resp_time', 'connector_resp_time', 'origin_resp_time']
        for int_candidate in int_fields:
            if d.get(int_candidate) and isDigit(d.get(int_candidate)):
                d[int_candidate] = int(d[int_candidate])
        for float_candidate in float_fields:
            if d.get(float_candidate) and isDigit(d.get(float_candidate)):
                d[float_candidate] = float(d[float_candidate])
        return d

    def get_api_url(self, logtype):
        prefix = ''
        logger.info(f"api_ver={self.api_ver}")
        if self.api_ver == common.BaseAPI.API_Version.OpenAPI:
            prefix = "mgmt-pop/"

        if logtype == self.EventType.ADMIN:
            return prefix + self.ADMINEVENT_API
        elif logtype == self.EventType.USER_ACCESS:
            return prefix + self.ACCESSLOG_API_V2
        else:
            raise Exception(f"Unknown access log type {logtype}")

    def parse_access_log(self, line):
        """
        Parse an EAA row access log line coming from EAA SIEM API
        This aligns with the official product documentation
        https://techdocs.akamai.com/eaa/docs/data-feed-siem#access-logs

        :param line: str EAA RAW log line
        :returns: dict with all the parsed fields
        """
        unknown_field = "???????"
        access_log_fields = {
            1:  "local_datetime",
            3:  "username",
            5:  "apphost",
            7:  "http_method",
            9:  "url_path",
            11: "http_ver",
            13: "referer",
            15: "status_code",
            17: "idpinfo",
            19: "clientip",
            21: "http_verb2",
            23: "total_resp_time",
            25: "connector_resp_time",
            27: "datetime",
            29: "origin_resp_time",
            31: "origin_host",
            33: "req_size",
            35: "content_type",
            37: "user_agent",
            39: "device_type",
            41: "device_os",
            43: "geo_city",
            45: "geo_state",
            47: "geo_statecode",
            49: "geo_countrycode",
            51: "geo_country",
            53: "internal_host",
            55: "session_info",
            57: "groups",
            59: "session_id",
            61: "client_id",
            63: "deny_reason",
            65: "bytes_out",
            67: "bytes_in",
            69: "con_ip",
            71: "con_srcport",
            73: "con_uuid",        # Introduced in EAA 2022.02
            75: "cloud_zone",      # Introduced in EAA 2022.02
            77: "error_code",      # Introduced in EAA 2022.02
            79: "client_process",  # Introduced in EAA 2022.02
            81: "client_version",  # Introduced in EAA 2022.02
            83: "srvty",           # Introduced in EAA 2025.03
            85: "appname"          # Introduced in EAA 2025.03
        }

        output_dict = {}
        debug_padding = 22

        logger.debug("------ begin debug log line -----")
        field_pos = 1  # follows techdoc logic
        for field in line.split(" "):
            if field_pos == 7:
                field7re = r'(?P<http_method>[A-Z]+)-(?P<url_path>.*)\-(?P<http_ver>HTTP/[0-9\.]*)'
                field7result = re.search(field7re, field)
                for subfieldkey in field7result.groupdict():
                    field_name = access_log_fields.get(field_pos, unknown_field)
                    logger.debug(f"#{field_pos:02} {field_name:>{debug_padding}}: {field7result[subfieldkey]}")
                    output_dict[field_name] = field7result[subfieldkey]
                    field_pos += 2
            elif field_pos == 69:
                if ":" in field:
                    for connector_ip_srcport in field.split(":"):
                        field_name = access_log_fields.get(field_pos, unknown_field)
                        logger.debug(f"#{field_pos:02} {field_name:>{debug_padding}}: {connector_ip_srcport}")
                        output_dict[field_name] = connector_ip_srcport
                        field_pos += 2
                else:
                    field_pos += 4  # Skip connector IP <semicolon> source port
            else:
                field_name = access_log_fields.get(field_pos, unknown_field)
                logger.debug(f"#{field_pos:02} {field_name:>{debug_padding}}: {field}")
                output_dict[field_name] = field
                field_pos += 2
        logger.debug("------ end debug log line -----")

        return output_dict

    def get_logs(self, drpc_args, logtype=EventType.USER_ACCESS, output=None):
        """
        Fetch the logs, by default the user access logs.
        """
        if not isinstance(logtype, self.EventType):
            raise ValueError("Unsupported log type %s" % logtype)
        scroll_id = None

        try:
            # Fetches the logs for given drpc args
            # 2021-09-08: Introduce a special retry mechanism for these API log endpoints
            #             only if there is a ConnectionError. Some data loss may occur as
            #             the remote server expect to deliver using a scrolling mechanism
            count = 0
            api_url = self.get_api_url(logtype)
            resp = self.post(api_url, json=drpc_args)
            logger.debug(f"Response HTTP/{resp.status_code}, "
                         f"HTTP header for POST {self._baseurl}{api_url} {resp.headers}")
            if not resp.headers.get('content-type'):
                logger.fatal(f"Content-Type header missing in response: POST {self._baseurl}{api_url} {resp.headers}")
                logger.fatal(f"Response body first 100 char: {resp.text[:100]}")
            if self.api_ver == common.BaseAPI.API_Version.Legacy and \
               RESPONSE_CONTENTTYPE not in resp.headers['content-type']:
                msg = (f"Invalid API response content-type: "
                       f"{resp.headers['content-type']}, expecting '{RESPONSE_CONTENTTYPE}'. "
                       f"URL: {resp.url}. "
                       f"Check your API host/credentials in section [{config.section}].")
                raise CLIFatalException(msg)
            if resp.status_code != 200:
                msg = "Invalid API response status code: %s" % resp.status_code
                raise CLIFatalException(msg)

            resj = resp.json()
            logger.debug("JSON> %s" % json.dumps(resj, indent=2))

            if 'message' in resj:
                if logtype == self.EventType.USER_ACCESS:
                    msg = resj.get('message')[0][1]
                    scroll_id = msg.get('scroll_id')
                elif logtype == self.EventType.ADMIN:
                    msg = resj.get('message')
                    if 'scroll_id' in msg.get('metadata'):
                        scroll_id = msg.get('metadata').get('scroll_id')
                else:
                    raise NotImplementedError("Doesn't support log type %s" % logtype)

                logger.debug("scroll_id: %s" % scroll_id)

                if logtype == self.EventType.USER_ACCESS:
                    for e in resj.get('message', [])[0][1].get('data', []):
                        local_time = datetime.datetime.fromtimestamp(e.get('ts')/1000)
                        line = "%s" % ' '.join([local_time.isoformat(), e.get('flog')])
                        if config.verbose or config.json:
                            parsed_dict = self.parse_access_log(line)
                        if config.json:
                            output.write("%s\n" % json.dumps(EventLogAPI.userlog_prepjson(parsed_dict)))
                        else:
                            output.write(line + "\n")
                        logger.debug(f"### flog v2 [{self.line_count}] ## {e}")
                        self.line_count += 1
                        count += 1
                elif logtype == self.EventType.ADMIN:
                    for item in msg.get('data'):
                        try:
                            local_time = datetime.datetime.fromtimestamp(int(item.get('ts')/1000),
                                                                         tz=datetime.timezone.utc)
                            line = u"{},{}\n".format(local_time.isoformat(), item.get('splunk_line'))
                            if config.json:
                                admin_event_data = line.split(',')
                                if isinstance(admin_event_data, list) and len(admin_event_data) == 6:
                                    admin_event_dict = {
                                        'datetime': admin_event_data[0],
                                        'username': admin_event_data[1],
                                        'resource_type': admin_event_data[2],
                                        'resource': admin_event_data[3],
                                        'event': admin_event_data[4],
                                        'event_type': admin_event_data[5].strip()
                                    }
                                    output.write("%s\n" % json.dumps(admin_event_dict))
                                else:
                                    cli.print_error("Error parsing line ")
                            else:
                                output.write(line)
                            self.line_count += 1
                            count += 1
                        except Exception as e:
                            logger.exception('Error parsing admin log line: %s, content: %s' %
                                              (e, item.get('splunk_line')))
            else:
                logger.error('Error: no data(message) in response.')
                logger.error(drpc_args)
                logger.error(json.dumps(resj))
                self.error_count += 1
            resp.close()
        except CLIFatalException:
            logger.exception("Fatal Exception")
            cli.exit(2)
        except requests.exceptions.RequestException:
            logger.exception("Fatal HTTP/API transaction")
            cli.exit(2)
        except Exception:
            if "resp" in locals():
                logger.debug("resp.status_code %s" % resp.status_code)
                logger.debug("resp.text %s" % resp.text)
            logger.error(drpc_args)
            logger.exception("Generic Exception")
        return (scroll_id, count)

    @staticmethod
    def date_boundaries(delay_sec):
        # end time in milliseconds, now minus collection delay
        ets = int(time.mktime(time.localtime()) * 1000 - (delay_sec * 1000))
        if config.end:
            ets = config.end * 1000
        # start time in milliseconds: end time minus poll interval
        sts = int(ets - (EventLogAPI.PULL_INTERVAL_SEC * 1000))
        if config.start:
            sts = config.start * 1000
        return ets, sts

    def fetch_logs(self, exit_fn, stop_event):
        """
        Fetch all logs until stop_event is set
        :param exit_fn:     function to call upon SIGTERM and SIGINT
        :param stop_event:  thread event, the fetch will operate in a loop until the event is set
        """
        log_type = self.EventType(config.log_type)
        logger.info(log_type)
        signal.signal(signal.SIGTERM, exit_fn)
        signal.signal(signal.SIGINT, exit_fn)

        logger.info("PID: %s" % os.getpid())
        logger.info("Poll interval: %s seconds" % EventLogAPI.PULL_INTERVAL_SEC)
        out = None
        count = 0

        try:
            if isinstance(self._output, str):
                logger.info("Output file: %s" % self._output)
                out = open(self._output, 'w+', encoding='utf-8')
            elif hasattr(self._output, 'write'):
                out = self._output
                if hasattr(out, 'reconfigure'):
                    out.reconfigure(encoding='utf-8')
            if out.seekable():
                start_position = out.tell()
            else:
                start_position = 0

            fetch_log_count = 0
            while not stop_event.is_set():
                delay_sec = max(config.delay, EventLogAPI.COLLECTION_MIN_DELAY_SEC)
                ets, sts = EventLogAPI.date_boundaries(delay_sec)
                s = time.time()
                logger.info("Fetching log[%s] from %s to %s..." % (log_type, sts, ets))
                if log_type == log_type.ADMIN:
                    if not config.batch and out.seekable():
                        cli.print("#DatetimeUTC,AdminID,ResourceType,Resource,Event,EventType")
                scroll_id = None
                while not stop_event.is_set():
                    drpc_args = {
                        'sts': str(sts),
                        'ets': str(ets),
                        'metrics': 'logs',
                        'es_fields': 'flog',
                        'limit': config.limit,
                        'sub_metrics': 'scroll',
                        'source': SOURCE
                    }
                    if scroll_id is not None:
                        drpc_args.update({'scroll_id': str(scroll_id)})
                    scroll_id, count = self.get_logs(drpc_args, log_type, out)
                    fetch_log_count += count
                    out.flush()
                    if scroll_id is None:
                        break
                if (not config.tail) or (config.start and config.end):
                    if not config.batch and out.seekable():
                        total_bytes = out.tell() - start_position
                        cli.print("# Start: %s (EPOCH %d)" %
                                  (time.strftime('%m/%d/%Y %H:%M:%S UTC', time.gmtime(sts/1000.)), sts/1000.))
                        cli.print("# End: %s (EPOCH %d)" %
                                  (time.strftime('%m/%d/%Y %H:%M:%S UTC', time.gmtime(ets/1000.)), ets/1000.))
                        cli.print("# Total: %s event(s), %s error(s), %s bytes written" %
                                  (self.line_count, self.error_count, total_bytes))
                        cli.print("Total time taken %s seconds" % (time.time() - s))
                    break
                else:
                    elapsed = time.time() - s
                    logger.debug("[config] Limit={}, Delay={} sec, Window={:.0f} ms".format(
                        self._config.limit, self._config.delay, ets-sts))
                    logger.debug(("[perf] {} event(s) took {:.3f} sec, "
                                  "fetch speed={:.1f} eps/{:,.0f} epm").format(fetch_log_count, elapsed,
                                  fetch_log_count/elapsed, 60*fetch_log_count/elapsed))
                    if elapsed > EventLogAPI.PULL_INTERVAL_SEC:
                        logger.warn("!! Data loss warning !! API request/responses takes too long. "
                                     "Check internet connectivity.")
                    logger.debug("Now waiting %s seconds..." % (EventLogAPI.PULL_INTERVAL_SEC - elapsed))
                    stop_event.wait(EventLogAPI.PULL_INTERVAL_SEC - elapsed)
                    fetch_log_count = 0
                    # TMESUP-147 when tail and start are set, we need to unset start
                    #            to kick in the normal tail
                    if config.tail and config.start:
                        logger.info("✴️✴️✴️ Engaging tail mode")
                        config.start = None
                    if stop_event.is_set():
                        break
        except Exception:
            logger.exception("General exception while fetching EAA logs")
        finally:
            if out and self._output != sys.stdout:
                logger.debug("Closing output file...")
                out.close()
            if self.line_count > 0:
                logger.info("%s log lines were fetched." % self.line_count)
