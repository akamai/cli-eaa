# Copyright 2022 Akamai Technologies, Inc. All Rights Reserved
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

"""
Common class / function for cli-eaa
"""

#: cli-eaa version [PEP 8]
__version__ = '0.5.9'

import sys
from threading import Event
import logging
import base64
import hmac
import hashlib
from urllib.parse import urljoin, parse_qs
from enum import Enum

# 3rd party libs
import six
import requests
from config import EdgeGridConfig
from akamai.edgegrid import EdgeGridAuth, EdgeRc


# If all parameters are set already, use them.  Otherwise
# use the config
config = EdgeGridConfig({'verbose': False}, 'default')

#: HTTP Request Timeout in seconds
HTTP_REQ_TIMEOUT = 300


class cli:
    """
    Utility methods for the CLI.
    """

    stop_event = Event()

    @staticmethod
    def print(s):
        sys.stdout.write("%s\n" % s)
        sys.stdout.flush()

    @staticmethod
    def print_error(s):
        sys.stderr.write("%s\n" % s)
        sys.stderr.flush()

    @staticmethod
    def header(s):
        if not config.batch:
            sys.stdout.write("%s\n" % s)
            sys.stdout.flush()

    @staticmethod
    def footer(s):
        if not config.batch:
            sys.stderr.write("%s\n" % s)
            sys.stderr.flush()

    @staticmethod
    def log_level():
        if config.debug:
            return logging.DEBUG
        elif config.verbose:
            return logging.INFO
        else:
            return logging.ERROR

    @staticmethod
    def exit(code):
        logging.info("Exit cli-eaa with code %s" % code)
        exit(code)

    @staticmethod
    def exit_gracefully(signum, frame):
        logging.info(f"Stop due to SIGTERM(15) or SIGINT(2) signal received: {signum} ")
        cli.stop_event.set()


class CLIFatalException(Exception):
    """
    When raised, this exception should cause the cli package to exit
    with a strictly positive error code.
    """
    pass


class EAALegacyAuth(requests.auth.AuthBase):
    """
    EAA legacy API authentication for Requests
    """
    def __init__(self, key, secret):
        self._key = key
        self._secret = secret
        self._signature = self.get_signature()

    def get_signature(self):
        encoding = 'ascii'
        msg = "%s:%s" % (self._key, self._secret)
        signature = hmac.new(
            key=self._secret.encode(encoding),
            msg=msg.encode(encoding),
            digestmod=hashlib.sha256).digest()
        signature = base64.b64encode(signature)
        return signature.decode(encoding)

    def __call__(self, r):
        r.headers.update({'Authorization': 'Basic %s:%s' % (self._key, self._signature)})
        r.headers.update({'Referer': '%s' % self._key[-6:]})
        return r


class EAAInvalidMoniker(Exception):
    pass


class EAAItem(object):
    """
    Representation of an EAA object.
    """
    _SEP = '://'

    class Type(Enum):

        Connector = "con"
        Application = "app"
        ApplicationGroupAssociation = "appgrp"
        Group = "group"
        User = "user"
        Directory = "dir"
        Certificate = "crt"
        IdentityProvider = "idp"

        @property
        def scheme(self):
            "Full prefix: object://."
            return "%s%s" % (self.value, EAAItem._SEP)

        @classmethod
        def has_value(cls, value):
            return value in [m[1].value for m in cls.__members__.items()]

    def __init__(self, obj_url):
        if not isinstance(obj_url, six.string_types):
            raise TypeError('obj_url must be a string')
        if EAAItem._SEP not in obj_url:
            raise EAAInvalidMoniker('Invalid EAA Object URL %s' % obj_url)
        scanned_type, scanned_uuid = obj_url.split(EAAItem._SEP)
        if EAAItem.Type.has_value(scanned_type):
            self.objtype = EAAItem.Type(scanned_type)
        else:
            raise ValueError('Invalid type "%s"' % scanned_type)
        self.uuid = scanned_uuid

    def __repr__(self):
        return self.objtype.scheme + self.uuid

    def __hash__(self):
        return self.__repr__().__hash__()

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return self.__str__() == other.__str__()

    def __neq__(self, other):
        return self.__str__() != other.__str__()


class BaseAPI(object):

    class API_Version(Enum):
        "API backend, either Legacy or {OPEN} API (support introduced in 2020 for EAA)."
        Legacy = 1
        OpenAPI = 2

    def __init__(self, config=None, api=API_Version.Legacy):

        self._config = config
        edgerc = EdgeRc(config.edgerc)
        section = config.section
        self.extra_qs = {}
        self.api_ver = api

        if self.api_ver == self.API_Version.Legacy:  # Prior to {OPEN} API, used for SIEM API only
            self._content_type_json = {'content-type': 'application/json'}
            self._content_type_form = \
                {'content-type': 'application/x-www-form-urlencoded'}
            self._headers = None
            # self._baseurl = 'https://%s' % edgerc.get(section, 'host')
            self._baseurl = 'https://%s/api/v1/' % edgerc.get(section, 'eaa_api_host',
                                                              fallback="manage.akamai-access.com")
            self._session = requests.Session()
            self._session.auth = EAALegacyAuth(
                edgerc.get(section, 'eaa_api_key'),
                edgerc.get(section, 'eaa_api_secret')
            )
            siem_api_adapter = requests.adapters.HTTPAdapter(
                max_retries=requests.adapters.Retry(total=5, backoff_factor=1, allowed_methods=["GET", "POST"])
            )
            self._session.mount("https://", siem_api_adapter)
        else:  # EAA {OPEN} API
            # TODO handle ambiguity when multiple contract ID are in use
            self._baseurl = 'https://%s/crux/v1/' % edgerc.get(section, 'host')
            self._session = requests.Session()
            self._session.auth = EdgeGridAuth.from_edgerc(edgerc, section)
            # Handle extra querystring to send to all REST requests
            scanned_extra_qs = edgerc.get(section, 'extra_qs', fallback=None)
            if scanned_extra_qs:
                self.extra_qs.update(parse_qs(scanned_extra_qs))

        if self._session:
            self._session.headers.update({'User-Agent': self.user_agent()})
            if config.proxy:
                logging.info("Set proxy to %s" % config.proxy)
                self._session.proxies['https'] = 'http://%s' % config.proxy

        logging.info("Initialized with base_url %s" % self._baseurl)

    def user_agent(self):
        return f"{self._config.ua_prefix} cli-eaa/{__version__}"

    def build_params(self, params=None):
        final_params = {"ua": self.user_agent()}
        final_params.update(self.extra_qs)
        if hasattr(self._config, 'contract_id') and self._config.contract_id:
            final_params.update({'contractId': self._config.contract_id})
        if isinstance(params, dict):
            final_params.update(params)
        return final_params

    @staticmethod
    def log_response_summary(response):
        """
        Log information about the API request/response to help with troubleshooting.
        """
        logging.info(f"BaseAPI: {response.url} {response.request.method} response is HTTP/{response.status_code}, "
                     f"x-trace-id: {response.headers.get('x-trace-id')}, "
                     f"x-ids-session-id: {response.headers.get('x-ids-session-id')}")

    def get(self, url_path, params=None):
        """
        Send a GET reques to the API.
        """
        url = urljoin(self._baseurl, url_path)
        response = self._session.get(url, params=self.build_params(params), timeout=HTTP_REQ_TIMEOUT)
        BaseAPI.log_response_summary(response)
        if response.status_code == 401:
            logging.fatal(f"API returned HTTP/401, check your API credentials\n{response.text}")
            logging.fatal(f"EdgeRC Section: {config.section}")
            cli.exit(401)
        if response.status_code != requests.status_codes.codes.ok:
            logging.info("BaseAPI: GET response body: %s" % response.text)
        return response

    def post(self, url_path, json=None, params=None, allow_redirects=True):
        url = urljoin(self._baseurl, url_path)
        logging.info("API URL: %s" % url)
        response = self._session.post(url, json=json, params=self.build_params(params),
                                      timeout=HTTP_REQ_TIMEOUT, allow_redirects=allow_redirects)
        BaseAPI.log_response_summary(response)
        if response.status_code != 200:
            logging.info("BaseAPI: POST response body: %s" % response.text)
        return response

    def put(self, url_path, json=None, params=None):
        url = urljoin(self._baseurl, url_path)
        logging.info("[PUT] API URL: %s" % url)
        response = self._session.put(url, json=json, params=self.build_params(params), timeout=HTTP_REQ_TIMEOUT)
        BaseAPI.log_response_summary(response)
        if response.status_code != 200:
            logging.info("BaseAPI: PUT response body: %s" % response.text)
        return response

    def delete(self, url_path, json=None, params=None):
        url = urljoin(self._baseurl, url_path)
        logging.info("API URL: %s" % url)
        response = self._session.delete(url, json=json, params=self.build_params(params), timeout=HTTP_REQ_TIMEOUT)
        BaseAPI.log_response_summary(response)
        if response.status_code != 200:
            logging.info("BaseAPI: DELETE response body: %s" % response.text)
        return response


def isfloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False
