#!/bin/bash

# Test update an existing application without ACL, add ACL
# https://track.akamai.com/jira/browse/EME-646

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
CLI_EAA="$SCRIPT_DIR/../bin/akamai-eaa"
TMP_FILE_PREFIX=$(mktemp)
export AKAMAI_EDGERC_SECTION="akamaidemo"

# Preparation
${CLI_EAA} version
cd "$SCRIPT_DIR/../docs/examples"
pwd

# Step 1, create an app without device posture
newapp_json=$(cat clientbasedapp-tunnel-noacl.json.j2 | ${CLI_EAA} -v --logfile "${TMP_FILE_PREFIX}.log" app - create)
newapp_uuid=$(echo $newapp_json|jq -r .uuid_url)
echo "New app UUID: ${newapp_uuid}"
echo "${newapp_json}" > "${TMP_FILE_PREFIX}.json"
echo "Log file: ${TMP_FILE_PREFIX}.log"
echo "App JSON file: ${TMP_FILE_PREFIX}.json"

# Step 2: append ACL service under the Services array
# Note: position is 1 because we assume there was no existing ACL
acl_rule='
{
    "action": 512,
    "description": null,
    "name": "Deny for Med/High Risk Device (added with JQ)",
    "position": 1,
    "rule_type": 1,
    "settings": [
        {
            "custom": false,
            "operator": "==",
            "type": "device_risk_tier",
            "value": "13"
        }
    ],
    "status": 1
}'

# Add an ACL to the list, enable ACL service
jq --argjson acl_rule "$acl_rule" '
(.Services[] | select (.service.service_type == 6)).access_rules += [ $acl_rule ] | 
(.Services[] | select (.service.service_type == 6)).service.status = "on"' \
${TMP_FILE_PREFIX}.json > ${TMP_FILE_PREFIX}-modified.json

# Step 3: post the update
cat ${TMP_FILE_PREFIX}-modified.json | ${CLI_EAA} -v --logfile "${TMP_FILE_PREFIX}.log" app app://${newapp_uuid} update

jq -r .name ${TMP_FILE_PREFIX}-modified.json


