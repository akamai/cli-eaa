# Python modules
from enum import Enum
import logging
import re
import requests
import datetime
import time

# cli-eaa modules
import util
from common import cli, BaseAPI, EAAItem


class DirectoryAPI(BaseAPI):
    """
    Interact with EAA directory configurations.
    """
    # class DirectoryType(Enum):
    #     CloudDirectory  7
    #     LDAP: 10,
    #     ActiveDirectory: 108

    class DirectoryStatus(Enum):
        Status3 = 3

    def __init__(self, configuration, directory_moniker=None):
        super(DirectoryAPI, self).__init__(configuration, BaseAPI.API_Version.OpenAPI)
        self._directory = None
        self._directory_id = None
        if directory_moniker:
            self._directory = EAAItem(directory_moniker)
            self._directory_id = self._directory.uuid

    def list_groups(self):
        url_params = {'limit': 0}
        url = 'mgmt-pop/directories/{directory_id}/groups'.format(directory_id=self._directory_id)
        if self._config.search_pattern:
            url_params = url_params.update({'q': self._config.search_pattern})
        resp = self.get(url, params=url_params)
        resj = resp.json()
        cli.header("#GroupID,name,last_sync")
        for u in resj.get('objects'):
            print('{scheme}{uuid},{name},{last_sync_time}'.format(
                scheme=EAAItem.Type.Group.scheme,
                uuid=u.get('uuid_url'),
                name=u.get('name'),
                last_sync_time=u.get('last_sync_time')
            ))

    def list_users(self, search=None):
        logging.info("SEARCH %s" % search)
        url_params = {'limit': 0}
        url = 'mgmt-pop/users'
        if search:
            url_params.update({'q': search})
        resp = self.get(url, params=url_params)
        resj = resp.json()
        for u in resj.get('objects'):
            cli.print("{scheme}{uuid},{fn},{ln}".format(
                scheme=EAAItem.Type.User.scheme,
                uuid=u.get('uuid_url'),
                fn=u.get('first_name'),
                ln=u.get('last_name')
            ))

    def list_directories(self):
        if self._directory_id:
            if self._config.users:
                if self._config.search_pattern and not self._config.batch:
                    cli.header("# list users matching %s in %s" % (self._config.search_pattern, self._directory_id))
                self.list_users(self._config.search_pattern)
            elif self._config.groups:
                if self._config.search_pattern and not self._config.batch:
                    cli.header("# list groups matching %s" % self._config.search_pattern)
                self.list_groups()
        else:
            resp = self.get("mgmt-pop/directories")
            if resp.status_code != 200:
                logging.error("Error retrieve directories (%s)" % resp.status_code)
            resj = resp.json()
            # print(resj)
            if not self._config.batch:
                cli.header("#dir_id,dir_name,status,user_count")
            total_dir = 0
            for total_dir, d in enumerate(resj.get("objects"), start=1):
                cli.print("{scheme}{dirid},{name},{status},{user_count}".format(
                    scheme=EAAItem.Type.Directory.scheme,
                    dirid=d.get("uuid_url"),
                    name=d.get("name"),
                    status=d.get("directory_status"),
                    user_count=d.get("user_count"))
                )
            if total_dir == 0:
                cli.footer("No EAA Directory configuration found.")
            elif total_dir == 1:
                cli.footer("One EAA Directory configuration found.")
            else:
                cli.footer("%d EAA Directory configurations found." % total_dir)

    def delgroup(self, group_id):
        raise NotImplementedError("Group deletion is not implemented")

    def deloverlaygroup(self, group_id):
        raise NotImplementedError("Group Overlay deletion is not implemented")
        url = "mgmt-pop/directories/{directory_id}/groups/{group_id}".format(
                directory_id=self._directory_id,
                group_id=group_id
            )
        self.delete(url)

    def addoverlaygroup(self, groupname):
        url = "mgmt-pop/directories/{directory_id}/groups".format(directory_id=self._directory_id)
        resp = self.post(url, json={"status": 1, "group_type": 4, "name": groupname})
        if resp.status_code != 200:
            logging.error("Error adding group to directory %s" % self._directory_id)
        else:
            cli.footer("Overlay group %s added to directory %s" % (groupname, self._directory_id))

    @staticmethod
    def groupname_from_dn(dn):
        """
        Extract the group name from a full Distinguished Name string.
        Reference: https://regexr.com/3l4au
        """
        regexp = '^(?:(?P<cn>CN=(?P<name>[^,]*)),)?(?:(?P<path>(?:(?:CN|OU)=[^,]+,?)+),)?(?P<domain>(?:DC=[^,]+,?)+)$'
        matches = re.search(regexp, dn)
        if matches:
            return matches.group('name')
        else:
            return False

    def addgroup(self, dn):
        """
        Add a group to EAA Directory configuration.
        :param dn: Distiguished Name of the group
                   Example: CN=Print Operators,CN=Builtin,DC=AKAMAIDEMO,DC=NET
        """
        url = "mgmt-pop/directories/{directory_id}/groups".format(directory_id=self._directory_id)
        for scanned_dn in util.argument_tolist((dn,)):
            group = DirectoryAPI.groupname_from_dn(scanned_dn)
            if group:
                logging.debug("Adding group %s" % (scanned_dn))
                resp = self.post(url, json={"name": group, "dn": scanned_dn})
                if resp.status_code != requests.status_codes.codes.ok:
                    logging.error(resp.status_code)
            else:
                logging.warn("Invalid DN: %s" % scanned_dn)

    def synchronize_group(self, group_uuid):
        """
        Synchronize a group within the directory

        Args:
            group_uuid (EAAItem): Group UUID e.g. grp://abcdef
        """
        """
        API call

        POST https://control.akamai.com/crux/v1/mgmt-pop/groups/16nUm7dCSyiihfCvMiHrMg/sync
        Payload: {}
        Response: {"response": "Syncing Group Sales Department"}
        """
        group = EAAItem(group_uuid)
        retry_remaining = self._config.retry + 1
        while retry_remaining > 0:
            retry_remaining -= 1
            cli.print("Synchronizing %s [retry=%s]..." % (group_uuid, retry_remaining))
            resp = self.get('mgmt-pop/directories/{dir_uuid}/groups/{group_uuid}'.format(
                dir_uuid=self._directory_id,
                group_uuid=group.uuid))
            if resp.status_code != 200:
                logging.error("Error retrieve group info (%s)" % resp.status_code)
                cli.exit(2)
            group_info = resp.json()
            if group_info.get('last_sync_time'):
                last_sync = datetime.datetime.fromisoformat(group_info.get('last_sync_time'))
                delta = datetime.datetime.utcnow() - last_sync
                cli.print("Last sync of group %s was @ %s UTC (%d seconds ago)" % (
                    group_info.get('name'),
                    last_sync,
                    delta.total_seconds())
                )
                if delta.total_seconds() > self._config.mininterval:
                    sync_resp = self.post('mgmt-pop/groups/{group_uuid}/sync'.format(group_uuid=group.uuid))
                    if sync_resp.status_code != 200:
                        cli.print_error("Fail to synchronize group (API response code %s)" % sync_resp.status_code)
                        cli.exit(3)
                    else:
                        cli.print("Synchronization of group %s (%s) successfully requested." %
                                  (group_info.get('name'), group))
                        break
                else:
                    cli.print_error("Last group sync is too recent, sync aborted. %s seconds interval is required." %
                                    self._config.mininterval)
                    if retry_remaining == 0:
                        cli.exit(2)
                    else:
                        sleep_time = last_sync + datetime.timedelta(seconds=self._config.mininterval) - \
                                     datetime.datetime.utcnow()
                        cli.print("Sleeping for %s, press Control-Break to interrupt" % sleep_time)
                        time.sleep(sleep_time.total_seconds())

    def synchronize(self):
        print("Synchronize whole directory %s..." % self._directory_id)
        response = self.post("mgmt-pop/directories/{dirId}/sync".format(dirId=self._directory_id))
        if response.status_code == 200 and not self._config.batch:
            print("Directory %s synchronization requested." % self._directory_id)
