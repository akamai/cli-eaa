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
import sys
import json

# cli-eaa
from common import cli, BaseAPI, EAAInvalidMoniker, EAAItem, config

# 3rd party
from jinja2 import Template


class ApplicationAPI(BaseAPI):
    """
    EAA Applications
    Only supported with {OPEN} API
    """

    LIMIT_INFINITE = 0  # Unless you know what you're doing
    LIMIT_SOFT = 10000  # Most tenant should accomodate this limit

    class Status(Enum):
        NotReady = 1
        Ready = 2
        Pending = 3
        Deployed = 4
        Failed = 5
        CloudDeployed = 6
        ConnectorDeploy = 7

    class Type(Enum):
        Hosted = 1
        SaaS = 2
        Bookmark = 3
        Tunnel = 4
        ETP = 5

    class Profile(Enum):
        HTTP = 1
        SharePoint = 2
        JIRA = 3
        RDP = 4
        VNC = 5
        SSH = 6
        Jenkins = 7
        Confluence = 8
        TCP = 9

    class Domain(Enum):
        Custom = 1
        Akamai = 2

    class ServiceType(Enum):
        ACL = 6

    def __init__(self, config):
        super(ApplicationAPI, self).__init__(config, api=BaseAPI.API_Version.OpenAPI)

    def process_command(self):
        """
        Process command passed from the CLI.
        """
        applications = list()
        appgroups = list()
        if self._config.application_id == '-':
            # nested if below because we don't do anything on create in this section
            if self._config.action != 'create':
                for line in sys.stdin:
                    scanned_items = line.split(',')
                    if len(scanned_items) == 0:
                        logging.warning("Cannot parse line: %s" % line)
                        continue
                    try:
                        scanned_obj = EAAItem(scanned_items[0])
                        if scanned_obj.objtype == EAAItem.Type.Application:
                            applications.append(scanned_obj)
                        elif scanned_obj.objtype == EAAItem.Type.ApplicationGroupAssociation:
                            appgroups.append(scanned_obj)
                    except EAAInvalidMoniker:
                        logging.warning("Invalid application moniker: %s" % scanned_items[0])
        else:
            logging.info("Single app %s" % config.application_id)
            applications.append(EAAItem(config.application_id))
            logging.info("%s" % EAAItem(config.application_id))

        if config.action == "deploy":
            for a in applications:
                self.deploy(a, config.comment)
                cli.print("Application %s deployment requested, it may take a few minutes before it gets live." % a)
        elif config.action == "create":
            # new_config = json.load(sys.stdin)
            new_config = sys.stdin.read()
            self.create(new_config)
        elif config.action == "update":
            if len(applications) > 1:
                raise Exception("Batch operation not supported")
            app = applications[0]
            new_config = json.load(sys.stdin)
            self.update(app, new_config)
            cli.print("Configuration for application %s has been updated." % app)
        elif config.action == "delete":
            for a in applications:
                self.delete_app(a)
        elif config.action == "add_dnsexception":
            for a in applications:
                self.add_dnsexception(a)
        elif config.action == "del_dnsexception":
            for a in applications:
                self.del_dnsexception(a)
        elif config.action == 'viewgroups':
            for a in applications:
                self.loadgroups(a)
        elif config.action == 'delgroup':
            for ag in appgroups:
                self.delgroup(ag)
        elif config.action in ('attach', 'detach'):
            for a in applications:
                connectors = []
                for c in set(config.connector_id):
                    con_moniker = EAAItem(c)
                    if con_moniker.objtype is not EAAItem.Type.Connector:
                        raise TypeError("Invalid type of connector: %s" % c)
                    connectors.append({"uuid_url": con_moniker.uuid})
                if config.action == 'attach':
                    self.attach_connectors(a, connectors)
                elif config.action == 'detach':
                    self.detach_connectors(a, connectors)
        else:  # view by default
            for a in applications:
                app_config = self.load(a)
                print(json.dumps(app_config))
                # print(app_config)

    def load(self, app_moniker, expand=True):
        """
        Load application configuration.
        :param expand: Set to True if you need extra details on inner objects (default is True)
        """
        # For the save/duplicate-type operations we need some extra data,
        # hence the two expand parameters
        url_params = {}
        if expand:
            url_params = {'expand': 'true', 'expand_sdk': 'true'}
        url = 'mgmt-pop/apps/{applicationId}'.format(applicationId=app_moniker.uuid)
        result = self.get(url, params=url_params)
        app_config = result.json()

        # Merge application groups info and align the view
        # to match the structure expected in save operation
        groups_url = 'mgmt-pop/apps/{applicationId}/groups'.format(applicationId=app_moniker.uuid)
        groups_result = self.get(groups_url, params={'limit': 0})
        groups = groups_result.json()
        app_config['groups'] = []
        for g in groups.get('objects', []):
            app_config['groups'].append(
                {
                    'name': g.get('group', {}).get('name'),
                    'enable_mfa': g.get('enable_mfa', 'inherit'),
                    'uuid_url': g.get('group', {}).get('group_uuid_url')
                }
            )

        # Merge URL path-based policies and align the view
        # to match the structure expected in save operation
        upp_url = 'mgmt-pop/apps/{applicationId}/urllocation'
        upp_result = self.get(upp_url.format(applicationId=app_moniker.uuid), params={'limit': 0})
        upp = upp_result.json()
        app_config['urllocation'] = []
        for upp_rule in upp.get('objects', []):
            app_config['urllocation'].append(upp_rule)

        return app_config

    def loadgroups(self, app_moniker):
        """Directory+Groups allowed to access this application."""
        url_params = {'limit': 0, 'expand': 'true', 'expand_sdk': 'true'}
        url = 'mgmt-pop/apps/{applicationId}/groups'.format(applicationId=app_moniker.uuid)
        result = self.get(url, url_params)
        count = 0
        allowed_groups = result.json().get('objects')
        if not self._config.batch:
            cli.header("# Allowed Groups to access app %s" % app_moniker)
            cli.header("# appgroup_id,group_id,group_name,dir_name,mfa")
        for count, group in enumerate(allowed_groups, start=1):
            association = group.get('resource_uri', {}).get('href')
            cli.print("{prefix1}{appgroup_id},{prefix2}{group_id},{name},{dir_name},{mfa}".format(
                prefix1=EAAItem.Type.ApplicationGroupAssociation.scheme,
                appgroup_id=association.split('/')[-1],
                prefix2=EAAItem.Type.Group.scheme,
                group_id=group.get('group').get('group_uuid_url'),
                name=group.get('group').get('name'),
                dir_name=group.get('group').get('dir_name'),
                mfa=group.get('enable_mfa')
            ))

        if not self._config.batch:
            cli.print("# %s groups configured to access application %s" % (count, app_moniker))
        return allowed_groups

    def delete_app(self, app_moniker):
        deletion = self.delete('mgmt-pop/apps/{applicationId}'.format(applicationId=app_moniker.uuid))
        if deletion.status_code == 200:
            cli.print("Application %s deleted." % app_moniker.uuid)

    def delgroup(self, appgroup_moniker):
        cli.print("Delete App-Group association %s..." % appgroup_moniker)
        deletion = self.post('mgmt-pop/appgroups', params={'method': 'DELETE'},
                             json={'deleted_objects': [appgroup_moniker.uuid]})
        if deletion.status_code == 200:
            cli.print("Association %s deleted." % appgroup_moniker)

    def cloudzone_lookup(self, name):
        """Lookup a cloud zone UUID based on it's name."""
        pops = self.get('mgmt-pop/pops?shared=true')
        for pop in pops.json().get('objects'):
            if pop.get('region') == name:
                return pop.get('uuid_url')
        return ""

    def certificate_lookup(self, cn):
        certs = self.get('mgmt-pop/certificates?limit=0')
        for cert in certs.json().get('objects'):
            if cert.get('cn') == cn:
                return cert.get('uuid_url')
        return ""

    def parse_template(self, raw_config):
        """
        Parse a template
        """
        t = Template(raw_config)
        t.globals['AppProfile'] = ApplicationAPI.Profile
        t.globals['AppType'] = ApplicationAPI.Type
        t.globals['AppDomainType'] = ApplicationAPI.Domain
        t.globals['cli_cloudzone'] = self.cloudzone_lookup
        t.globals['cli_certificate'] = self.certificate_lookup
        output = t.render()
        logging.debug("JSON Post-Template Render:")
        for lineno, line in enumerate(output.splitlines()):
            logging.debug("{:4d}> {}".format(lineno+1, line))
        return output

    def create(self, raw_app_config):
        """
        Create a new EAA application configuration.
        :param app_config: configuration as JSON string

        Note: the portal use the POST to create a new app with a minimal payload:
              {"app_profile":1,"app_type":1,"client_app_mode":1,"app_profile_id":"Fp3RYok1EeSE6AIy9YR0Dw",
              "name":"tes","description":"test"}
              We should do the same here
        """
        app_config = json.loads(self.parse_template(raw_app_config))
        logging.debug("Post Jinja parsing:\n%s" % json.dumps(app_config))
        app_config_create = {
            "app_profile": app_config.get('app_profile'),
            "app_type": app_config.get('app_type', ApplicationAPI.Type.Hosted.value),
            "name": app_config.get('name'),
            "description": app_config.get('description')
        }
        newapp = self.post('mgmt-pop/apps', json=app_config_create)
        logging.info("Create app core: %s %s" % (newapp.status_code, newapp.text))
        if newapp.status_code != 200:
            cli.exit(2)
        newapp_config = newapp.json()
        logging.info("New app JSON:\n%s" % newapp.text)
        app_moniker = EAAItem("app://{}".format(newapp_config.get('uuid_url')))
        logging.info("UUID of the newapp: %s" % app_moniker)

        # Now we push everything else as a PUT
        self.put('mgmt-pop/apps/{applicationId}'.format(applicationId=app_moniker.uuid), json=app_config)

        # Sub-components of the application configuration definition

        # --- Connectors
        if app_config.get('agents'):
            self.attach_connectors(app_moniker, app_config.get('agents', []))

        # IdP, Directories, Groups
        self.create_auth(app_moniker, app_config)

        # --- Access Control rules
        self.create_acl(app_moniker, app_config)

        # --- Other services
        # TODO: implement

        # URL based policies
        self.create_urlbasedpolicies(app_moniker, app_config)

        # At the end we reload the app entirely
        cli.print(json.dumps(self.load(app_moniker)))

    def create_acl(self, app_moniker, app_config):
        """
        Save ACL rules into a newly created EAA application
        :param app_moniker: identifier of the newly created app
        :app_config: details of the configuration to save
        """
        # UUID for the ACL service in the newly created application
        logging.debug("Fetch service UUID...")
        services_resp = self.get('mgmt-pop/apps/{app_uuid}/services'.format(app_uuid=app_moniker.uuid))
        service_uuid = None
        logging.info(json.dumps(services_resp.json(), indent=4))
        for s in services_resp.json().get('objects', []):
            scanned_service_type = s.get('service', {}).get('service_type')
            logging.debug("Scanned service_type: %s" % scanned_service_type)
            if scanned_service_type == ApplicationAPI.ServiceType.ACL.value:
                service_uuid = s.get('service', {}).get('uuid_url')
                break  # Only one service of type ACL
        logging.debug("Service UUID for the app is %s" % service_uuid)

        if service_uuid:

            # Obtain ACL service details from the input configuration
            service_acl = None
            for s in app_config.get('Services', []):
                scanned_service_type = s.get('service', {}).get('service_type')
                logging.info("Scanned service_type: %s" % scanned_service_type)
                if scanned_service_type == ApplicationAPI.ServiceType.ACL.value:
                    service_acl = s
                    break  # Only one service of type ACL

            if not service_acl:
                logging.warning("No acl rules defined in the application configuration JSON document, skipping")
                return

            # Enable the ACL service
            # payload = {"uuid_url":"fJZ7A0emQWijZ40mxB3dWw","description":null,"name":"Access Control",
            # service_type":6,"settings":{},"status":"on"}
            payload = service_acl.get('service')
            payload['uuid_url'] = service_uuid
            self.put(
                'mgmt-pop/services/{service_uuid}'.format(service_uuid=service_uuid),
                json=payload
            )

            for acl_rule in service_acl.get('access_rules', []):
                # Step 1 create the Rules to get the corresponding UUID
                new_acl_rule = self.post(
                    'mgmt-pop/services/{service_uuid}/rules'.format(service_uuid=service_uuid),
                    json={"rule_type": acl_rule.get('rule_type', 1), "name": acl_rule.get('name')}
                )
                new_acl_rule_uuid = new_acl_rule.json().get('uuid_url')
                # Step 2 save the details of the rules
                self.put('mgmt-pop/rules/{rule_uuid}'.format(rule_uuid=new_acl_rule_uuid), json=acl_rule)

        else:

            logging.warning("Unable to find a ACL service in the newly created application %s" % app_moniker)

    def create_auth(self, app_moniker, app_config):
        """
        Create application authentication configuration
        IdP, Directories, Groups
        """
        # IdP
        # The "view" operation gives us the IdP in idp -> idp_id
        scanned_idp_uuid = app_config.get('idp', {}).get('idp_id')
        if scanned_idp_uuid:
            idp_app_payload = {"app": app_moniker.uuid, "idp": scanned_idp_uuid}
            idp_app_resp = self.post('mgmt-pop/appidp', json=idp_app_payload)
            logging.info("IdP-app association response: %s %s" % (idp_app_resp.status_code, idp_app_resp.text))

        # Directory
        # The view operation gives us the directories in directories[] -> uuid_url
        scanned_directories = app_config.get('directories', [])
        app_directories_payload = {"data": [{"apps": [app_moniker.uuid], "directories": scanned_directories}]}
        app_directories_resp = self.post('mgmt-pop/appdirectories', json=app_directories_payload)
        logging.info(
            "App directories association response: %s %s" %
            (app_directories_resp.status_code, app_directories_resp.text)
        )
        if app_directories_resp.status_code != 200:
            cli.exit(2)
        # Groups
        if len(app_config.get('groups', [])) > 0:
            app_groups_payload = {'data': [{'apps': [app_moniker.uuid], 'groups': app_config.get('groups', [])}]}
            app_groups_resp = self.post('mgmt-pop/appgroups', json=app_groups_payload)
            if app_groups_resp.status_code != 200:
                cli.exit(2)
        else:
            logging.debug("No group set")

    def create_urlbasedpolicies(self, app_moniker, app_config):
        if len(app_config.get('urllocation', [])) > 0:
            upp_url = 'mgmt-pop/apps/{applicationId}/urllocation'.format(applicationId=app_moniker.uuid)
            for upp_rule in app_config.get('urllocation', []):
                upp_create_payload = {
                    "rule_type": upp_rule.get("rule_type", 1),
                    "name": upp_rule.get("name"),
                    "url": upp_rule.get("url")
                }
                upp_create = self.post(upp_url, json=upp_create_payload)
                upp_create_data = upp_create.json()
                if upp_create_data.get('uuid_url'):
                    upp_update_url = 'mgmt-pop/apps/{applicationId}/urllocation/{ruleId}'
                    self.put(upp_update_url.format(
                        applicationId=app_moniker.uuid,
                        ruleId=upp_create_data.get('uuid_url')),
                        json=upp_rule
                    )
        else:
            logging.debug("No URL path-based policies set")

    def update(self, app_moniker, app_config):
        """
        Update an existing EAA application configuration.
        """
        update = self.put(
            'mgmt-pop/apps/{applicationId}'.format(applicationId=app_moniker.uuid),
            json=app_config
        )
        logging.info("Update app response: %s" % update.status_code)
        logging.info("Update app response: %s" % update.text)
        if update.status_code != 200:
            cli.exit(2)

    def attach_connectors(self, app_moniker, connectors):
        """
        Attach connector/s to an application.

        :param EAAItem app_moniker: Application Moniker (prefix + UUID)
        :param list connectors: Connector list, expected list item format is dict {'uuid_url': '<UUID>'}
        """
        # POST on mgmt-pop/apps/DBMcU6FwSjKa7c9sny4RLg/agents
        # Body
        # {"agents":[{"uuid_url":"cht3_GEjQWyMW9LEk7KQfg"}]}
        logging.info("Attaching {} connectors...".format(len(connectors)))
        api_resp = self.post(
            'mgmt-pop/apps/{applicationId}/agents'.format(applicationId=app_moniker.uuid),
            json={'agents': connectors}
        )
        logging.info("Attach connector response: %s" % api_resp.status_code)
        logging.info("Attach connector app response: %s" % api_resp.text)
        if api_resp.status_code not in (200, 201):
            cli.print_error("Connector(s) %s were not attached to application %s [HTTP %s]" %
                            (','.join([c.get('uuid_url') for c in connectors]), app_moniker, api_resp.status_code))
            cli.print_error("use 'akamai eaa -v ...' for more info")
            cli.exit(2)

    def detach_connectors(self, app_moniker, connectors):
        """
        Detach connector/s to an application.
        Payload is different from attach above:
        {"agents":["cht3_GEjQWyMW9LEk7KQfg"]}
        """
        logging.info("Detaching {} connectors...".format(len(connectors)))
        api_resp = self.post(
            'mgmt-pop/apps/{applicationId}/agents'.format(applicationId=app_moniker.uuid),
            params={'method': 'delete'}, json={'agents': [c.get('uuid_url') for c in connectors]}
        )
        logging.info("Detach connector response: %s" % api_resp.status_code)
        logging.info("Detach connector app response: %s" % api_resp.text)
        if api_resp.status_code not in (200, 204):
            cli.print_error("Connector(s) %s were not detached from application %s [HTTP %s]" %
                            (','.join([c.get('uuid_url') for c in connectors]), app_moniker, api_resp.status_code))
            cli.print_error("use 'akamai eaa -v ...' for more info")
            cli.exit(2)

    def add_dnsexception(self, app_moniker):
        logging.info("Adding DNS exception: %s" % config.exception_fqdn)
        appcfg = self.load(app_moniker)
        dns_exceptions = set(appcfg.get('advanced_settings', {}).get('domain_exception_list').split(','))
        dns_exceptions |= set(config.exception_fqdn)
        appcfg["advanced_settings"]["domain_exception_list"] = ','.join(dns_exceptions)
        self.save(app_moniker, appcfg)

    def del_dnsexception(self, app_moniker):
        logging.info("Remove DNS exception: %s" % config.exception_fqdn)
        pass

    def deploy(self, app_moniker, comment=""):
        """
        Deploy an EAA application.
        """
        if not isinstance(app_moniker, EAAItem):
            raise TypeError("Deploy expect and EAAItem, %s provided" % type(app_moniker))
        if app_moniker.objtype != EAAItem.Type.Application:
            raise ValueError("EAAItem object must be app, %s found" % app_moniker.objtype.value)
        payload = {}
        if comment:
            payload["deploy_note"] = comment
        deploy = self.post('mgmt-pop/apps/{applicationId}/deploy'.format(applicationId=app_moniker.uuid), json=payload)
        logging.info("ApplicationAPI: deploy app response: %s" % deploy.status_code)
        if deploy.status_code != 200:
            logging.error(deploy.text)
