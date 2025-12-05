# Copyright 2025 Akamai Technologies, Inc. All Rights Reserved
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
import os
import string
import random

# cli-eaa
from common import cli, BaseAPI, EAAInvalidMoniker, EAAItem, config, merge_dicts

# 3rd party
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


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

    class ClientMode(Enum):
        TCP = 1
        Tunnel = 2

    def __init__(self, config, api=BaseAPI.API_Version.OpenAPI):
        "Force the config arg to passed on."
        super(ApplicationAPI, self).__init__(config, api=api)

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
                        logger.warning("Cannot parse line: %s" % line)
                        continue
                    try:
                        scanned_obj = EAAItem(scanned_items[0])
                        if scanned_obj.objtype == EAAItem.Type.Application:
                            applications.append(scanned_obj)
                        elif scanned_obj.objtype == EAAItem.Type.ApplicationGroupAssociation:
                            appgroups.append(scanned_obj)
                    except EAAInvalidMoniker:
                        logger.warning("Invalid application moniker: %s" % scanned_items[0])
        else:
            logger.info("Single app %s" % config.application_id)
            applications.append(EAAItem(config.application_id))
            logger.info("%s" % EAAItem(config.application_id))

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
            new_config = sys.stdin.read()
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
            for a in applications:
                self.delgroup(a)
        elif config.action == 'addgroup':
            for a in applications:
                appgrps = []
                for ag in set(config.appgrp_id):
                    appgrp_moniker = EAAItem(ag)
                    appgrps.append(appgrp_moniker.uuid)
                self.addgroup(a, appgrps)
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
            url_params = {'expand': expand, 'expand_sdk': expand}
        url = 'mgmt-pop/apps/{applicationId}'.format(applicationId=app_moniker.uuid)
        result = self.get(url, params=url_params)
        app_config = result.json()

        if expand:

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

    def addgroup(self, app_moniker, appgrps):
        cli.print("Add App-group(s) %s to %s ..." % (', '.join(appgrps), app_moniker))
        addition = self.post('mgmt-pop/appgroups',
                              json = {"data":[{"apps":[app_moniker.uuid],"groups": [{"uuid_url": "" + gi + "","enable_mfa":"inherit"} for gi in appgrps]}]})
        if addition.status_code == 200:
            cli.print("Association %s added." % (', '.join(appgrps)))

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

    def connector_lookup(self, name):
        agents = self.get('mgmt-pop/agents?limit=100')
        for agent in agents.json().get('objects'):
            if agent.get('name') == name:
                return agent.get('uuid_url')
        return ""
    
    def idp_lookup(self, name):
        idps = self.get('mgmt-pop/idp?limit=100')
        for idp in idps.json().get('objects'):
            if idp.get('name') == name:
                logger.debug(json.dumps(idp, indent=2))
                return idp
        return None

    def directory_lookup(self, name):
        directories = self.get('mgmt-pop/directories?limit=100')
        for dir in directories.json().get('objects'):
            if dir.get('name') == name:
                logger.debug(json.dumps(dir, indent=2))
                return dir
        return None
    
    def group_lookup(self, directory_uuid, group_name):
        logger.debug(f"group_lookup: looking for {group_name} in directory {directory_uuid}...")
        url = 'mgmt-pop/directories/{directory_uuid}/groups'.format(directory_uuid=directory_uuid)     
        groups = self.get(url)
        for g in groups.json().get('objects'):
            if g.get('name') == group_name:
                logger.debug("### FOUND GROUP")
                logger.debug(json.dumps(g, indent=2))
                return g
        return None
    
    def random_string(self, length):
        characters = string.ascii_lowercase + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    def parse_template(self, raw_config):
        """
        Parse the EAA configuration as JINJA2 template
        """
        logger.debug("Jinja template loader base directory: %s" % os.getcwd())
        t = Environment(loader=FileSystemLoader(os.getcwd())).from_string(raw_config)
        t.globals['AppProfile'] = ApplicationAPI.Profile
        t.globals['AppType'] = ApplicationAPI.Type
        t.globals['AppDomainType'] = ApplicationAPI.Domain
        t.globals['cli_cloudzone'] = self.cloudzone_lookup
        t.globals['cli_certificate'] = self.certificate_lookup
        t.globals['cli_connector'] = self.connector_lookup
        t.globals['cli_idp'] = self.idp_lookup
        t.globals['cli_directory'] = self.directory_lookup
        t.globals['cli_group'] = self.group_lookup
        t.globals['cli_randomstring'] = self.random_string
        output = t.render(**dict(self._config.variables))
        logger.debug("JSON Post-Template Render:")
        for lineno, line in enumerate(output.splitlines()):
            logger.debug("{:4d}> {}".format(lineno+1, line))
        return output

    def create(self, raw_app_config):
        """
        Create a new EAA application configuration.
        :param app_config: configuration as JSON string

        Note: the portal use the POST to create a new app with a minimal payload:
              {"app_profile":1,"app_type":1,"client_app_mode":1,"app_profile_id":"●●●●●●●●●●●●●●●●●●●●●●",
              "name":"test app","description":"This is my test app"}
              We should do the same here
        """
        app_config = json.loads(self.parse_template(raw_app_config))
        logger.debug("Post Jinja parsing:\n%s" % json.dumps(app_config))
        app_config_create = {
            "app_profile": app_config.get('app_profile'),
            "app_type": app_config.get('app_type', ApplicationAPI.Type.Hosted.value),
            "name": app_config.get('name'),
            "description": app_config.get('description')
        }
        # Client based app mode must be set (TCP mode is the default otherwise)
        if app_config.get('client_app_mode'):
            app_config_create["client_app_mode"] = \
                app_config.get('client_app_mode', ApplicationAPI.ClientMode.TCP.value)
        newapp = self.post('mgmt-pop/apps', json=app_config_create)

        if config.debug:
            json_object = json.dumps(app_config_create, indent=4)        
            with open(f"1_POST_{app_config.get('name')}.json", "w") as outfile:
                outfile.write(json_object)

        logger.info("Create app core: %s %s" % (newapp.status_code, newapp.text))
        if newapp.status_code != 200:
            cli.exit(2)
        newapp_config = newapp.json()
        logger.info("New app JSON:\n%s" % newapp.text)
        app_moniker = EAAItem("app://{}".format(newapp_config.get('uuid_url')))
        logger.info("UUID of the newapp: %s" % app_moniker)

        # Now we push everything else as a PUT (update)
        self.put('mgmt-pop/apps/{applicationId}'.format(applicationId=app_moniker.uuid), json=app_config)

        if config.debug:
            json_object = json.dumps(app_config, indent=4)        
            with open(f"2_PUT_{app_config.get('name')}.json", "w") as outfile:
                outfile.write(json_object)

        # Sub-components of the application configuration definition

        # --- Connectors
        if app_config.get('agents'):
            self.attach_connectors(app_moniker, app_config.get('agents', []))

        # IdP, Directories, Groups
        self.create_auth(app_moniker, app_config)

        # --- Access Control rules
        self.set_acl(app_moniker, app_config)

        # --- Other services
        # TODO: implement

        # URL based policies
        self.create_urlbasedpolicies(app_moniker, app_config)

        # At the end we reload the app entirely
        cli.print(json.dumps(self.load(app_moniker)))

    def set_acl(self, app_moniker, app_config):
        """
        Save ACL rules into a newly created EAA application
        :param app_moniker: identifier of the newly created app
        :app_config: details of the configuration to save
        """
        # UUID for the ACL service in the newly created application
        logger.debug("Fetch service UUID...")
        services_resp = self.get('mgmt-pop/apps/{app_uuid}/services'.format(app_uuid=app_moniker.uuid))
        service_uuid = None
        logger.info(json.dumps(services_resp.json(), indent=4))
        for s in services_resp.json().get('objects', []):
            scanned_service_type = s.get('service', {}).get('service_type')
            logger.debug("Scanned service_type: %s" % scanned_service_type)
            if scanned_service_type == ApplicationAPI.ServiceType.ACL.value:
                service_uuid = s.get('service', {}).get('uuid_url')
                break  # Only one service of type ACL
        logger.debug("Service UUID for the app is %s" % service_uuid)

        if service_uuid:

            # Obtain ACL service details from the input configuration
            service_acl = None
            for s in app_config.get('Services', []):
                scanned_service_type = s.get('service', {}).get('service_type')
                logger.info("Scanned service_type: %s" % scanned_service_type)
                if scanned_service_type == ApplicationAPI.ServiceType.ACL.value:
                    service_acl = s
                    break  # Only one service of type ACL

            if not service_acl:
                logger.warning("No acl rules defined in the application configuration JSON document, skipping")
                return

            # Enable the ACL service
            # payload = {"uuid_url":"●●●●●●●●●●●●●●●●●●●●●●","description":null,"name":"Access Control",
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

            logger.warning("Unable to find a ACL service in the newly created application %s" % app_moniker)

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
            logger.info("IdP-app association response: %s %s" % (idp_app_resp.status_code, idp_app_resp.text))

        # Directory
        # The view operation gives us the directories in directories[] -> uuid_url
        scanned_directories = app_config.get('directories', [])
        app_directories_payload = {"data": [{"apps": [app_moniker.uuid], "directories": scanned_directories}]}
        app_directories_resp = self.post('mgmt-pop/appdirectories', json=app_directories_payload)
        logger.info(
            "App directories association response: %s %s" %
            (app_directories_resp.status_code, app_directories_resp.text)
        )
        if app_directories_resp.status_code != 200:
            cli.exit(2)

        # Groups
        self.set_appgroups(app_moniker, app_config)

    def create_urlbasedpolicies(self, app_moniker, app_config):
        if len(app_config.get('urllocation', [])) > 0:
            upp_url = 'mgmt-pop/apps/{applicationId}/urllocation'.format(applicationId=app_moniker.uuid)
            for upp_rule in app_config.get('urllocation', []):

                # First we create the URL Policy url skeleton
                upp_create_payload = {
                    "rule_type": upp_rule.get("rule_type", 1),
                    "name": upp_rule.get("name"),
                    "url": upp_rule.get("url")
                }
                upp_create = self.post(upp_url, json=upp_create_payload)
                upp_create_data = upp_create.json()

                if upp_create_data.get('uuid_url'):
                    upp_update_url = 'mgmt-pop/apps/{applicationId}/urllocation/{ruleId}'
                    # Merge incoming settings with default set by backend provided
                    put_payload = merge_dicts(upp_create_data, upp_rule)
                    self.put(upp_update_url.format(
                        applicationId=app_moniker.uuid,
                        ruleId=upp_create_data.get('uuid_url')),
                        json=put_payload
                    )
        else:
            logger.debug("No URL path-based policies set")

    def update(self, app_moniker, raw_app_config):
        """
        Update an existing EAA application configuration.
        """
        postjj_app_config = self.parse_template(raw_app_config)
        try:
            app_config = json.loads(postjj_app_config)
        except json.decoder.JSONDecodeError as jde:
            for lineno, line in enumerate(postjj_app_config.splitlines()):
                logger.error("{:4d}> {}".format(lineno+1, line))
            raise jde

        # App core property update
        update = self.put(
            'mgmt-pop/apps/{applicationId}'.format(applicationId=app_moniker.uuid),
            json=app_config
        )
        logger.info(f"Update core app HTTP/{update.status_code}: {update.text}")
        if update.status_code != 200:
            cli.exit(2)

        # Update Access Control Rules
        self.set_acl(app_moniker, app_config)

        # Directory/Group
        self.set_appgroups(app_moniker, app_config)

    def set_appgroups(self, app_moniker, app_config):
        # TODO: use this method in create_auth to set_auth to better fit both create and update
        # self.create_auth(app_moniker, app_config)

        # Update require to pull the latest list of group (on Akamai Cloud)
        # compare with what's in the incoming payload
        # new groups added to mgmt-pop/appgroups?
        # payload: {'data': [{'apps': [app_moniker.uuid], 'groups': app_config.get('groups', [])}]}
        # remove groups that are not in the incoming payload to mgmt-pop/appgroups?method=DELETE
        # {"deleted_objects":["●●●●●●●●●●●●●●●●●●●●●●"]}
        # where the UUID in the list is the app group UUID
        # Example
        # Add "support"
        # {"data":[{"apps":["●●●●●●●●●●●●●●●●●●●●●●"],"groups":[{"uuid_url":"●●●●●●●●●●●●●●●●●●●●●●","enable_mfa":"inherit"}]}]}
        # Remove "support"
        # {"deleted_objects":["●●●●●●●●●●●●●●●●●●●●●●"]}

        if app_config.get('groups'):  # if the group key is not in the json, we don't touch anything
            existing_groups_resp = self.get(f'mgmt-pop/apps/{app_moniker.uuid}/groups/', params={'limit': 0})
            existing_groups = existing_groups_resp.json().get('objects', [])
            existing_groups_uuid_map = dict()  # mapping between group UUID and app-group UUID association
            logger.debug(f"existing_groups_resp:\n{json.dumps(existing_groups, indent=2)}")
            existing_group_uuids = set()
            for appgroup in existing_groups:
                scan_dirguuid = appgroup.get('group', {}).get('group_uuid_url')
                scan_apguuid = appgroup.get('uuid_url')
                existing_group_uuids.add(scan_dirguuid)
                existing_groups_uuid_map[scan_dirguuid] = scan_apguuid

            incoming_group_uuids = set()
            for appgroup in app_config.get('groups', []):
                incoming_group_uuids.add(appgroup.get('uuid_url'))

            logger.debug(f"existing_appgroup_uuids={existing_group_uuids}")
            logger.debug(f"incoming_appgroup_uuids={incoming_group_uuids}")

            # Groups to delete
            delete_payload = {"deleted_objects": []}
            for group_uuid_to_delete in (existing_group_uuids - incoming_group_uuids):
                logger.debug(f"Deleting group UUID {group_uuid_to_delete}, "
                             f"appgroup UUID {existing_groups_uuid_map[group_uuid_to_delete]}...")
                delete_payload["deleted_objects"].append(existing_groups_uuid_map[group_uuid_to_delete])
            logger.debug(f"payload: {delete_payload}")
            self.post('mgmt-pop/appgroups', params={'method': "DELETE"}, json=delete_payload)

            # Group to add/ensure are presents
            if len(app_config.get('groups', [])) > 0:
                app_groups_payload = {'data': [{'apps': [app_moniker.uuid], 'groups': app_config.get('groups', [])}]}
                app_groups_resp = self.post('mgmt-pop/appgroups', json=app_groups_payload)
                if app_groups_resp.status_code != 200:
                    cli.exit(2)
            else:
                logger.debug("No access groups set.")

    def attach_connectors(self, app_moniker, connectors):
        """
        Attach connector/s to an application.

        :param EAAItem app_moniker: Application Moniker (prefix + UUID)
        :param list connectors: Connector list, expected list item format is dict {'uuid_url': '<UUID>'}
        """
        # POST on mgmt-pop/apps/●●●●●●●●●●●●●●●●●●●●●●/agents
        # Body
        # {"agents":[{"uuid_url":"●●●●●●●●●●●●●●●●●●●●●●"}]}
        logger.info("Attaching {} connectors...".format(len(connectors)))
        api_resp = self.post(
            'mgmt-pop/apps/{applicationId}/agents'.format(applicationId=app_moniker.uuid),
            json={'agents': connectors}
        )
        logger.info("Attach connector response: %s" % api_resp.status_code)
        logger.info("Attach connector app response: %s" % api_resp.text)
        if api_resp.status_code not in (200, 201):
            cli.print_error("Connector(s) %s were not attached to application %s [HTTP %s]" %
                            (','.join([c.get('uuid_url') for c in connectors]), app_moniker, api_resp.status_code))
            cli.print_error("use 'akamai eaa -v ...' for more info")
            cli.exit(2)

    def detach_connectors(self, app_moniker, connectors):
        """
        Detach connector/s to an application.
        Payload is different from attach above:
        {"agents":["●●●●●●●●●●●●●●●●●●●●●●"]}
        """
        logger.info("Detaching {} connectors...".format(len(connectors)))
        api_resp = self.post(
            'mgmt-pop/apps/{applicationId}/agents'.format(applicationId=app_moniker.uuid),
            params={'method': 'delete'}, json={'agents': [c.get('uuid_url') for c in connectors]}
        )
        logger.info("Detach connector response: %s" % api_resp.status_code)
        logger.info("Detach connector app response: %s" % api_resp.text)
        if api_resp.status_code not in (200, 204):
            cli.print_error("Connector(s) %s were not detached from application %s [HTTP %s]" %
                            (','.join([c.get('uuid_url') for c in connectors]), app_moniker, api_resp.status_code))
            cli.print_error("use 'akamai eaa -v ...' for more info")
            cli.exit(2)

    def add_dnsexception(self, app_moniker):
        logger.info("Adding DNS exception: %s" % config.exception_fqdn)
        appcfg = self.load(app_moniker)
        dns_exceptions = set(appcfg.get('advanced_settings', {}).get('domain_exception_list').split(','))
        dns_exceptions |= set(config.exception_fqdn)
        appcfg["advanced_settings"]["domain_exception_list"] = ','.join(dns_exceptions)
        self.save(app_moniker, appcfg)

    def del_dnsexception(self, app_moniker):
        logger.info("Remove DNS exception: %s" % config.exception_fqdn)

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
        logger.info("ApplicationAPI: deploy app response: %s" % deploy.status_code)
        if deploy.status_code != 200:
            logger.error(deploy.text)

    def list(self, fields: list=[], details: bool=False):
        """
        List all applications (experimental)
        :param details (bool): load the app details (SUPER SLOW)
        """

        if self.api_ver != BaseAPI.API_Version.OpenAPIv3:
            raise Exception("Unsupported API version")
        
        app_fields = set(["uuid_url"] + fields)

        total_count = None
        page = 1
        page_size = 100
        offset = 0
        l = []

        app_config_loader = ApplicationAPI(self._config, BaseAPI.API_Version.OpenAPI)
        while total_count == None or len(l) < total_count:
            r = self.get('mgmt-pop/apps', params={"offset": offset, "fields": ",".join(app_fields), 
                                                  "limit": page_size, "offset": (page-1)*page_size})
            j = r.json()
            total_count = j.get('meta').get('total_count')
            page += 1
            for a in j.get('objects'):
                if details:
                    l.append(app_config_loader.load(EAAItem(f"app://{a.get('uuid_url')}"), expand=False))
                else:
                    l.append(a)
        return l

    def stats_by_cloudzone(self):
        if self.api_ver != BaseAPI.API_Version.OpenAPIv3:
            raise Exception("Unsupported API version")

        appcount_by_cloudzone = {}
        for a in self.list(details=True):
            scanned_cloudzone = a.get('popRegion')
            if scanned_cloudzone not in appcount_by_cloudzone.keys():
                appcount_by_cloudzone[scanned_cloudzone] = 0
            appcount_by_cloudzone[scanned_cloudzone] += 1
        return appcount_by_cloudzone
    
    def entdns_stats_by_cloudzone(self):
        "Special app 'Enterprise DNS'."
        entdns_count_by_cloudzone = {}
        r = self.get("mgmt-pop/childdns?limit=0")
        entdns_response = r.json()
        for e in entdns_response.get('objects'):
            scanned_cloudzone = e.get('popRegion')
            if scanned_cloudzone not in entdns_count_by_cloudzone.keys():
                entdns_count_by_cloudzone[scanned_cloudzone] = 0
            entdns_count_by_cloudzone[scanned_cloudzone] += 1
        return entdns_count_by_cloudzone
