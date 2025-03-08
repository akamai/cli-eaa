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

# cli-eaa
from common import cli, BaseAPI
from application import ApplicationAPI

MAX_RESULT = 1000
logger = logging.getLogger(__name__)

class IdentityProviderAPI(BaseAPI):
    """
    EAA IdP
    """
    def __init__(self, config):
        super(IdentityProviderAPI, self).__init__(config, api=BaseAPI.API_Version.OpenAPI)

    def load(self, idp_moniker):
        api_idp = self.get('mgmt-pop/idp/{idp}'.format(idp=idp_moniker.uuid))
        if api_idp.status_code != 200:
            raise Exception("Error loading IdP %s configuration" % idp_moniker)
        return api_idp.json()

    def list(self):
        url_params = {'limit': MAX_RESULT}
        search_idp = self.get('mgmt-pop/idp', params=url_params)
        cli.header("#IdP-id,name,idp_hostname,status,certificate,client,dp")
        idps = search_idp.json()
        logger.debug(idps)
        for i in idps.get('objects', []):
            cli.print("idp://{idp_id},{name},{host},{status},{cert},{client},{dp}".format(
                idp_id=i.get('uuid_url'),
                name=i.get('name'),
                host=i.get('login_host'),
                status=ApplicationAPI.Status(i.get('idp_status')).name,
                cert=(("crt://%s" % i.get('cert')) if i.get('cert') else '-'),
                client=('Y' if i.get('enable_access_client') else 'N'),
                dp=('Y' if i.get('enable_device_posture') else 'N')
            ))

    def deploy(self, idp_moniker):
        """
        POST https://control.akamai.com/crux/v1/mgmt-pop/idp/{idp_id}/deploy
        Payload: {}
        """
        deploy_idp = self.post('mgmt-pop/idp/{idp_id}/deploy'.format(idp_id=idp_moniker.uuid), json={})
        if deploy_idp.status_code != 200:
            raise Exception("Error deploying IdP %s HTTP %s" %
                            (idp_moniker, deploy_idp.status_code))

    def stats_by_pop(self):
        """
        Build a dictionnary with key being the EAA POP name, 
        and value the number of IdP configuration deployed.
        """
        idp_by_pop_uuid = {}
        url_params = {'limit': MAX_RESULT}
        search_idp = self.get('mgmt-pop/idp', params=url_params)
        idps = search_idp.json()

        for idp in idps.get('objects'):
            pop_uuid = idp.get('pop')
            if not pop_uuid in idp_by_pop_uuid.keys():
                idp_by_pop_uuid[pop_uuid] = 0
            idp_by_pop_uuid[pop_uuid] += 1

        return idp_by_pop_uuid
