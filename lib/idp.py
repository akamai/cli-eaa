# cli-eaa
from common import cli, BaseAPI
from application import ApplicationAPI

MAX_RESULT = 1000


class IdentityProviderAPI(BaseAPI):
    """
    EAA IdP
    """
    def __init__(self, config):
        super(IdentityProviderAPI, self).__init__(config, api=BaseAPI.API_Version.OpenAPI)

    def list(self):
        url_params = {'limit': MAX_RESULT}
        search_idp = self.get('mgmt-pop/idp', params=url_params)
        cli.header("#IdP-id,name,status,certificate,client,dp")
        idps = search_idp.json()
        for i in idps.get('objects', []):
            cli.print("idp://{idp_id},{name},{status},{cert},{client},{dp}".format(
                idp_id=i.get('uuid_url'),
                name=i.get('name'),
                status=ApplicationAPI.Status(i.get('idp_status')).name,
                cert=(("crt://%s" % i.get('cert')) if i.get('cert') else '-'),
                client=('Y' if i.get('enable_access_client') else 'N'),
                dp=('Y' if i.get('enable_device_posture') else 'N')
            ))

    def deploy(self, idp_id):
        """
        POST https://control.akamai.com/crux/v1/mgmt-pop/idp/{idp_id}/deploy
        Payload: {}
        """
        deploy_idp = self.post('mgmt-pop/idp/{idp_id}'.format(idp_id=idp_id), json={})
        if deploy_idp.status_code == 200:
            cli.print("Deployment for IdP %s requested..." % idp_id)
