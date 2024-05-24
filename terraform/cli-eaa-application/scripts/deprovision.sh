#!/bin/bash

# Deprovision an EAA application with CLI-EAA
# based on environment variables
# Author: Antoine Drochon <androcho@akamai.com>
# Date: May 2024

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source $DIR/eaa-app-lib.sh

log_message "Starting $0..."
sanity_checks

# Create temporary edgerc credentials file
AKAMAI_EDGERC=$(build_edgerc)

log_message "Removing EAA application named ${APP_NAME}..."
log_message "Check if an application named '$APP_NAME' exists..."
APP_UUID=$("${CLIEAA_COMMAND}" --edgerc $AKAMAI_EDGERC search | awk -F, "\$3 == \"$APP_NAME\" { print \$1 }")

if [ "${APP_UUID}" != "" ]; then
    log_message "Found application as $APP_UUID"
    "${CLIEAA_COMMAND}" --edgerc "${AKAMAI_EDGERC}" app ${APP_UUID} delete && echo Application ${APP_UUID} removed.
else
    log_message "$(date -u +%Y-%m-%dT%H:%M:%S.%N) WARNING: EAA application with name ${APP_NAME} was not found on this account." "ERROR"
fi
