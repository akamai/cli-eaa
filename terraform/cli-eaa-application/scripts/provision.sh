#!/bin/bash

# Provision an EAA application with CLI-EAA
# based on environment variables
# Author: Antoine Drochon <androcho@akamai.com>
# Date: May 2024

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source $DIR/eaa-app-lib.sh

log_message "Starting $0..."
sanity_checks create

# Create temporary edgerc credentials file
AKAMAI_EDGERC=$(build_edgerc)

# Check if the application exists
log_message "Check if an application named '$APP_NAME' exists..."
APP_UUID=$(${CLIEAA_COMMAND} --edgerc $AKAMAI_EDGERC search | awk -F, "\$3 == \"$APP_NAME\" { print \$1 }")

if [ "$APP_UUID" == "" ]; then
  # create use case
  APP=$(cat ${DIR}/tunnapp.j2.json | 
    ${CLIEAA_COMMAND} --edgerc $AKAMAI_EDGERC app - create \
      --var APP_NAME "${APP_NAME}" \
      --var APP_DESCRIPTION "${APP_DESCRIPTION}" \
      --var CLOUDZONE_NAME "${CLOUDZONE_NAME}" \
      --var CONNECTOR_NAMES "${CONNECTOR_NAMES}" \
      --var TUNNEL_DESTINATION_HOST_OR_IP "${TUNNEL_DESTINATION_HOST_OR_IP}" \
      --var TUNNEL_DESTINATION_PORTS "${TUNNEL_DESTINATION_PORTS}" \
      --var IDP_NAME "${IDP_NAME}" \
      --var DIRECTORY_NAME "${DIRECTORY_NAME}" \
      --var GROUP_NAMES "${GROUP_NAMES}") \
    || die "Error creating the EAA application configuration"

  APP_UUID=$(echo "${APP}" | jq .uuid_url)
  log_message "APP_UUID=$APP_UUID" DEBUG

  if [ "$DEPLOY" == "1" ]; then
    log_message Deploying the app...
    APP_UUID=$(${CLIEAA_COMMAND} --edgerc $AKAMAI_EDGERC search | awk -F, "\$3 == \"$APP_NAME\" { print \$1 }")
    ${CLIEAA_COMMAND} --edgerc $AKAMAI_EDGERC app $APP_UUID deploy
  fi
else
  # update
  cat ${DIR}/tunnapp.j2.json | 
    ${CLIEAA_COMMAND} --edgerc $AKAMAI_EDGERC app "${APP_UUID}" update \
      --var APP_NAME "${APP_NAME}" \
      --var APP_DESCRIPTION "${APP_DESCRIPTION}" \
      --var CLOUDZONE_NAME "${CLOUDZONE_NAME}" \
      --var CONNECTOR_NAMES "${CONNECTOR_NAMES}" \
      --var TUNNEL_DESTINATION_HOST_OR_IP "${TUNNEL_DESTINATION_HOST_OR_IP}" \
      --var TUNNEL_DESTINATION_PORTS "${TUNNEL_DESTINATION_PORTS}" \
      --var IDP_NAME "${IDP_NAME}" \
      --var DIRECTORY_NAME "${DIRECTORY_NAME}" \
      --var GROUP_NAMES "${GROUP_NAMES}" \
    || die "Error updating the EAA application configuration"
fi

log_message "Clean up..."
[ "$VIRTUAL_ENV" != "" ] && deactivate
test -f "${AKAMAI_EDGERC}" && rm -f -v "${AKAMAI_EDGERC}"
