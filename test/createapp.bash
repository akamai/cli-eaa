#!/bin/bash

# Due to application configuration template
# with some relative directories, we use this bash script
# to perform application creation test.
# See the cli-eaa.bats for the main test sequence

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
CLI="$1" # CLI command
if [[ "$CLI" == "" ]]; then
    CLI="$SCRIPT_DIR/../bin/akamai-eaa"
fi

if ! command -v mktemp; then
    echo "ERROR: mktemp does not exist on this system."
    exit 2
fi

EAA_CONFIG=$( mktemp )
echo "CLI: $CLI"
echo "EAA Application Configuration: $EAA_CONFIG"

cd "$SCRIPT_DIR/../docs/examples"
cat clientbasedapp-tunnel.json.j2 | ${CLI} app - create > "$EAA_CONFIG"
echo "CLI return code: $?"

APPLICATION_NAME=$(cat "$EAA_CONFIG" | jq -r ".name")
APPLICATION_UUID=$(cat "$EAA_CONFIG" | jq -r ".uuid_url")

echo "APPLICATION_UUID: $APPLICATION_UUID"
echo "Application name: $APPLICATION_NAME"
echo "Delete $EAA_CONFIG local file..."
if [ -f "$EAA_CONFIG" ]; then
    rm "$EAA_CONFIG"
fi
echo "Deleting the EAA app..."
${CLI} app "app://$APPLICATION_UUID" delete
echo "Deletion RC: $?"