#!/usr/bin/env python3

import requests
from akamai.edgegrid import EdgeGridAuth, EdgeRc
from urllib.parse import urljoin
import json
import logging

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    edgerc = EdgeRc('/Users/androcho/.edgerc')
    section = 'default'
    baseurl = 'https://%s' % edgerc.get(section, 'host')

    s = requests.Session()
    s.auth = EdgeGridAuth.from_edgerc(edgerc, section)

    result = s.get(urljoin(baseurl, '/crux/v1/mgmt-pop/apps/{applicationId}'.format(applicationId="p2ZvLbdgSjeulbF4kq3_tA")))
    if result.status_code != 200:
        exit(2)

    eaa_config = result.json()
    dns_exceptions = eaa_config.get('advanced_settings', {}).get('domain_exception_list').split(',')
    print(dns_exceptions)

    # Let's add a domain
    dns_exceptions.append('some.domain.ltd')

    eaa_config["advanced_settings"]["domain_exception_list"] = ','.join(dns_exceptions)

    print(json.dumps(eaa_config, indent=4, sort_keys=True))
    update = s.put(urljoin(baseurl, '/crux/v1/mgmt-pop/apps/{applicationId}'.format(applicationId="p2ZvLbdgSjeulbF4kq3_tA")), json=eaa_config)
    print("update app response: ", update.status_code)
    print(update.text)

 #   deploy = s.get(urljoin(baseurl, '/crux/v1/mgmt-pop/apps/{applicationId}/deploy'.format(applicationId="p2ZvLbdgSjeulbF4kq3_tA")))
 #   print("deploy app response: ", deploy.status_code)
