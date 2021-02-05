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
from enum import Enum
import logging
import json

from common import cli, BaseAPI, EAAItem, config
from application import ApplicationAPI


class CertificateAPI(BaseAPI):
    """
    Manage EAA certificates
    Example of command using this class:
    - Rotate a certificate
      akamai eaa cert crt:/123456 rotate --cert mycert.pem --key mycert.key
    """

    class Type(Enum):
        Custom = 1
        UNK = 2
        SelfSigned = 5
        CertificateAuthority = 6

    def __init__(self, config):
        super(CertificateAPI, self).__init__(config, api=BaseAPI.API_Version.OpenAPI)

    def list(self):
        url_params = {'expand': 'true', 'limit': 0}
        data = self.get('mgmt-pop/certificates', params=url_params)
        certificates = data.json()
        total_cert = 0
        logging.info(json.dumps(data.json(), indent=4))
        cli.print('#Certificate-ID,cn,type,expiration,days left')
        format_line = "{scheme}{uuid},{cn},{cert_type},{expiration},{days_left}"
        for total_cert, c in enumerate(certificates.get('objects', {}), start=1):
            cli.print(format_line.format(
                scheme=EAAItem.Type.Certificate.scheme,
                uuid=c.get('uuid_url'),
                cn=c.get('cn'),
                cert_type=CertificateAPI.Type(c.get('cert_type')).name,
                expiration=c.get('expired_at'),
                days_left=c.get('days_left')
            ))
        cli.footer("Total %s certificate(s)" % total_cert)

    def rotate(self):
        """
        Update an existing certificate.
        """
        cert_moniker = EAAItem(self._config.certificate_id)
        cli.print("Rotating cert %s..." % cert_moniker.uuid)
        api_url = 'mgmt-pop/certificates/{certificate_id}'.format(certificate_id=cert_moniker.uuid)

        get_resp = self.get(api_url)
        current_cert = get_resp.json()
        # cli.print(json.dumps(current_cert, sort_keys=True, indent=4))

        payload = {}
        payload['name'] = current_cert.get('name')
        payload['cert_type'] = current_cert.get('cert_type')
        with self._config.cert as f:
            payload['cert'] = f.read()
        with self._config.key as f:
            payload['private_key'] = f.read()
        if self._config.passphrase:
            payload['password'] = self._config.passphrase
        put_resp = self.put(api_url, json=payload, params={'expand': 'true', 'limit': 0})
        if put_resp.status_code == 200:
            new_cert = put_resp.json()
            cli.footer(("Certificate %s updated, %s application(s) and %s directory(ies) "
                        "have been marked ready for deployment.") %
                       (cert_moniker.uuid, new_cert.get('app_count'), new_cert.get('dir_count')))
            if self._config.deployafter:
                self.deployafter(cert_moniker.uuid)
            else:
                cli.footer("Please deploy at your convience.")
        else:
            cli.print_error("Error rotating cert, see response below:")
            cli.print_error(put_resp.text)
            cli.exit(2)

    def findappsbycert(self, certid):
        """Find application using certificate identified by `certid`"""
        url_params = {'limit': 10000}
        search_app = self.get('mgmt-pop/apps', params=url_params)
        apps = search_app.json()
        for a in apps.get('objects', []):
            if a.get('cert') == certid:
                yield (EAAItem("app://%s" % a.get('uuid_url')), a.get('name'))

    def findidpbycert(self, certid):
        """Find IdP using certificate identified by `certid`"""
        url_params = {'limit': 10000}
        search_idp = self.get('mgmt-pop/idp', params=url_params)
        idps = search_idp.json()
        for i in idps.get('objects', []):
            if i.get('cert') == certid:
                yield (EAAItem("idp://%s" % i.get('uuid_url')), i.get('name'))

    def deployafter(self, certid):
        app_api = ApplicationAPI(config)
        for app_id, app_name in self.findappsbycert(certid):
            cli.print("Deploying application %s..." % app_name)
            app_api.deploy(app_id)
        for idp_id, idp_name in self.findidpbycert(certid):
            cli.print("Deploying IdP %s..." % idp_name)

    def delete(self):
        raise NotImplementedError("deletion not implemented")
        pass
