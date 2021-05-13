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
import six

# cli-eaa modules
import common
from common import config, cli, isfloat

SOURCE = 'akamai-cli/eaa'


class EventLogAPI(common.BaseAPI):
    """
    EAA logs, this is using the legacy EAA API
    Inspired by EAA Splunk app
    """

    #: Pull interval when using the tail mode
    PULL_INTERVAL_SEC = 15
    COLLECTION_DELAY_MINUTES = 1

    class EventType(Enum):
        USER_ACCESS = "access"
        ADMIN = "admin"

    ADMINEVENT_API = "adminevents-reports/ops/splunk-query"
    ACCESSLOG_API = "analytics/ops"

    def __init__(self, config):
        super(EventLogAPI, self).__init__(config, api=common.BaseAPI.API_Version.Legacy)
        self._content_type_json = {'content-type': 'application/json'}
        self._content_type_form = {'content-type': 'application/x-www-form-urlencoded'}
        self._headers = None
        self._output = config.output
        if not self._output:
            self._output = sys.stdout
        self.line_count = 0
        self.error_count = 0
        # Pre-compile the dictionary output
        userlog_pattern = r'^([^\s]*)\s(?P<username>[\w\-]*)\s(?P<apphost>[\w\.\-]+)\s(?P<http_method>[A-Z]+)-(?P<url_path>.*)\-(?P<http_ver>HTTP/[0-9\.]*)\s(?P<referer>[^\s]*)\s(?P<status_code>[0-9]*)\s(?P<idpinfo>[^\s]*)\s(?P<clientip>[^\s]*)\s(?P<http_verb2>[^\s]*)\s(?P<total_resp_time>[^\s]*)\s(?P<connector_resp_time>[^\s]*)\s(?P<datetime>[^\s]*)\s(?P<origin_resp_time>[^\s]*)\s(?P<origin_host>[^\s]*)\s(?P<req_size>[^\s]*)\s(?P<content_type>[^\s]*)\s(?P<user_agent>[^\s]*)\s(?P<device_os>[^\s]*)\s(?P<device_type>[^\s]*)\s(?P<geo_city>[^\s]*)\s(?P<geo_state>[^\s]*)\s(?P<geo_statecode>[^\s]*)\s(?P<geo_countrycode>[^\s]*)\s(?P<geo_country>[^\s]*)\s(?P<internal_host>[^\s]*)\s(?P<session_info>[^\s]*)\s(?P<groups>[^\s]*)\s(?P<session_id>.*)[\s.*|]'
        self._userlog_regexp = re.compile(userlog_pattern)

    def userlog_prepjson(d):
        if str.isdigit(d.get('req_size')):
            d['req_size'] = int(d['req_size'])
        if str.isdigit(d.get('status_code')):
            d['status_code'] = int(d['status_code'])
        if isfloat(d.get('total_resp_time')):
            d['total_resp_time'] = float(d['total_resp_time'])
        return d

    def get_api_url(self, logtype):
        if logtype == self.EventType.ADMIN:
            return self.ADMINEVENT_API
        else:
            return self.ACCESSLOG_API

    def get_logs(self, drpc_args, logtype=EventType.USER_ACCESS, output=None):
        """
        Fetch the logs, by default the user access logs.
        """
        if not isinstance(logtype, self.EventType):
            raise ValueError("Unsupported log type %s" % logtype)

        scroll_id = None
        try:
            # Fetches the logs for given drpc args
            resp = self.post(self.get_api_url(logtype), json=drpc_args)
            if resp.status_code != requests.codes.ok:
                logging.error("Invalid API response status code: %s" % resp.status_code)
                return None

            resj = resp.json()
            logging.debug("JSON> %s" % json.dumps(resj, indent=2))

            if 'message' in resj:
                # Get msg and scroll_id based on the type of logs
                # Since it is two different API in the back-end
                if logtype == self.EventType.USER_ACCESS:
                    msg = resj.get('message')[0][1]
                    scroll_id = msg.get('scroll_id')
                elif logtype == self.EventType.ADMIN:
                    msg = resj.get('message')
                    if 'scroll_id' in msg.get('metadata'):
                        scroll_id = msg.get('metadata').get('scroll_id')
                else:
                    raise NotImplementedError("Doesn't support log type %s" % logtype)

                logging.debug("scroll_id: %s" % scroll_id)
                count = 0

                if logtype == self.EventType.USER_ACCESS:
                    for timestamp, response in six.iteritems(msg):
                        try:
                            if not timestamp.isdigit():
                                logging.debug("Ignored timestamp '%s': %s" % (timestamp, response))
                                continue
                            logging.debug("flog is %s" % type(response['flog']).__name__)
                            logging.debug("Scanned timestamp: %s" % timestamp)
                            if int(timestamp) < int(drpc_args.get('sts')):
                                raise Exception("Out of bound error: incoming event time %s vs. start set to %s" % (timestamp, drpc_args.get('sts')))
                            if int(timestamp) >= int(drpc_args.get('ets')):
                                raise Exception("Out of bound error: incoming event time %s vs. end set to %s" % (timestamp, drpc_args.get('ets')))
                            local_time = datetime.datetime.fromtimestamp(int(timestamp)/1000)
                            if isinstance(response, dict) and 'flog' in response:
                                line = "%s\n" % ' '.join([local_time.isoformat(), response['flog']])
                                if config.json:
                                    result = self._userlog_regexp.search(line)
                                    cli.print(json.dumps(EventLogAPI.userlog_prepjson(result.groupdict())))
                                else:
                                    output.write(line)
                                logging.debug("### flog ## %s" % response['flog'])
                                self.line_count += 1
                                count += 1
                        except Exception:
                            logging.exception("Error parsing access log line")
                elif logtype == self.EventType.ADMIN:
                    for item in msg.get('data'):
                        try:
                            local_time = datetime.datetime.fromtimestamp(int(item.get('ts')/1000))
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
                                    output.write(json.dumps(admin_event_dict))
                                    output.write("\n")
                                else:
                                    cli.print_error("Error parsing line ")
                            else:
                                output.write(line)
                            self.line_count += 1
                            count += 1
                        except Exception as e:
                            logging.exception('Error parsing admin log line: %s, content: %s' %
                                              (e, item.get('splunk_line')))
            else:
                logging.error('Error: no data(message) in response.')
                logging.error(drpc_args)
                logging.error(json.dumps(resj))
                self.error_count += 1
            resp.close()
        except Exception:
            if "resp" in locals():
                logging.debug("resp.status_code %s" % resp.status_code)
                logging.debug("resp.text %s" % resp.text)
            logging.error(drpc_args)
            logging.exception("Exception in get_logs")
        return scroll_id

    @staticmethod
    def date_boundaries():
        # end time in milliseconds, now minus collection delay
        ets = int(time.mktime(time.localtime()) * 1000 - (EventLogAPI.COLLECTION_DELAY_MINUTES * 60 * 1000))
        if not config.tail and config.end:
            ets = config.end * 1000
        # start time in milliseconds: end time minus poll interval
        sts = int(ets - (EventLogAPI.PULL_INTERVAL_SEC * 1000))
        if not config.tail and config.start:
            sts = config.start * 1000
        return ets, sts

    def fetch_logs(self, exit_fn, stop_event):
        """
        Fetch all logs until stop_event is set
        :param exit_fn:     function to call upon SIGTERM and SIGINT
        :param stop_event:  thread event, the fetch will operate in a loop until the event is set
        """
        log_type = self.EventType(config.log_type)
        logging.info(log_type)
        signal.signal(signal.SIGTERM, exit_fn)
        signal.signal(signal.SIGINT, exit_fn)

        logging.info("PID: %s" % os.getpid())
        logging.info("Poll interval: %s seconds" % EventLogAPI.PULL_INTERVAL_SEC)
        out = None
        try:
            if isinstance(self._output, str):
                logging.info("Output file: %s" % self._output)
                out = open(self._output, 'w+', encoding='utf-8')
            elif hasattr(self._output, 'write'):
                out = self._output
                if hasattr(out, 'reconfigure'):
                    out.reconfigure(encoding='utf-8')
            if out.seekable():
                start_position = out.tell()
            else:
                start_position = 0

            while True:
                ets, sts = EventLogAPI.date_boundaries()
                s = time.time()
                logging.info("Fetching log[%s] from %s to %s..." % (log_type, sts, ets))
                if log_type == log_type.ADMIN:
                    if not config.batch:
                        cli.print("#DatetimeUTC,AdminID,ResourceType,Resource,Event,EventType")
                out.write
                scroll_id = None
                while (True):
                    drpc_args = {
                        'sts': str(sts),
                        'ets': str(ets),
                        'metrics': 'logs',
                        'es_fields': 'flog',
                        'limit': '1000',
                        'sub_metrics': 'scroll',
                        'source': SOURCE,
                    }
                    if scroll_id is not None:
                        drpc_args.update({'scroll_id': str(scroll_id)})
                    scroll_id = self.get_logs(drpc_args, log_type, out)
                    out.flush()
                    if scroll_id is None:
                        break
                if not config.tail:
                    if not config.batch:
                        total_bytes = out.tell() - start_position
                        cli.print("# Start: %s (EPOCH %d)" %
                                  (time.strftime('%m/%d/%Y %H:%M:%S UTC', time.gmtime(sts/1000.)), sts/1000.))
                        cli.print("# End: %s (EPOCH %d)" %
                                  (time.strftime('%m/%d/%Y %H:%M:%S UTC', time.gmtime(ets/1000.)), ets/1000.))
                        cli.print("# Total: %s event(s), %s error(s), %s bytes written" %
                                  (self.line_count, self.error_count, total_bytes))
                    break
                else:
                    elapsed = time.time() - s
                    logging.debug("Now waiting %s seconds..." % (EventLogAPI.PULL_INTERVAL_SEC - elapsed))
                    stop_event.wait(EventLogAPI.PULL_INTERVAL_SEC - elapsed)
                    if stop_event.is_set():
                        break
        except Exception:
            logging.exception("General exception while fetching EAA logs")
        finally:
            if out and self._output != sys.stdout:
                logging.debug("Closing output file...")
                out.close()
            logging.info("%s log lines were fetched." % self.line_count)
