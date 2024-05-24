function log_message() {

    MSG=$1
    SEV=$2

    COLOR_RED='\033[0;31m'
    COLOR_GREEN='\033[0;32m'
    COLOR_NONE='\033[0m'

    [ "$SEV" == "" ] && SEV="INFO"

    if [ "$LOG_FILE" == "" ]; then
        case "$SEV" in
            DEBUG | D)
                # Colored message on stderr
                echo -e "$(date -u +%Y-%m-%dT%H:%M:%S) ${COLOR_GREEN}[${SEV}] ${MSG}${COLOR_NONE}" 1>&2
                ;;            
            ERROR | E)
                # Colored message on stderr
                echo -e "$(date -u +%Y-%m-%dT%H:%M:%S) ${COLOR_RED}[${SEV}] ${MSG}${COLOR_NONE}" 1>&2
                ;;
            *)
                echo "$(date -u +%Y-%m-%dT%H:%M:%S) [${SEV}] ${MSG}"
                ;;
        esac
    else
        echo "$(date -u +%Y-%m-%dT%H:%M:%S) [${SEV}] ${MSG}" >> "${LOG_FILE}"
    fi
}

function sanity_checks() {

    if [ "${APP_NAME}" == "" ]; then echo "Missing APP_NAME"; exit 1; fi
    if [ "${OPENAPI_HOST}" == "" ]; then echo "Missing OPENAPI_HOST"; exit 1; fi
    if [ "${OPENAPI_CLIENT_SECRET}" == "" ]; then echo "Missing OPENAPI_CLIENT_SECRET"; exit 1; fi
    if [ "${OPENAPI_ACCESS_TOKEN}" == "" ]; then echo "Missing OPENAPI_ACCESS_TOKEN"; exit 1; fi
    if [ "${OPENAPI_CLIENT_TOKEN}" == "" ]; then echo "Missing OPENAPI_CLIENT_TOKEN"; exit 1; fi

    if [ "$1" == "create" ]; then

        if [ "${CLOUDZONE_NAME}" == "" ]; then echo "Missing CLOUDZONE_NAME"; exit 1; fi
        if [ "${TUNNEL_DESTINATION_HOST_OR_IP}" == "" ]; then echo "Missing TUNNEL_DESTINATION_HOST_OR_IP"; exit 1; fi
        if [ "${TUNNEL_DESTINATION_PORTS}" == "" ]; then echo "Missing TUNNEL_DESTINATION_PORTS"; exit 1; fi
        if [ "${CONNECTOR_NAMES}" == "" ]; then echo "Missing CONNECTOR_NAMES"; exit 1; fi

    fi

    [ "$CLIEAA_COMMAND" == "" ] && export CLIEAA_COMMAND="akamai eaa"

    log_message "cli-eaa command: ${CLIEAA_COMMAND}" DEBUG
    CLIEAA_VER=$(${CLIEAA_COMMAND} version || die "cli-eaa command error $?: $CLIEAA_COMMAND" 2)
    log_message "cli-eaa version: ${CLIEAA_VER}" DEBUG
}

function build_edgerc() {
    AKAMAI_EDGERC=$(mktemp)
    cat > "${AKAMAI_EDGERC}" << EOT
[default]
client_secret = ${OPENAPI_CLIENT_SECRET}
host = ${OPENAPI_HOST}
access_token = ${OPENAPI_ACCESS_TOKEN}
client_token = ${OPENAPI_CLIENT_TOKEN}
account_key = ${ACCOUNT_KEY}
extra_qs = accountSwitchKey=${ACCOUNT_KEY}
# end of file
EOT
    echo "${AKAMAI_EDGERC}"
}

die () {
    msg="$1"
    rc=1
    [ "$2" != "" ] && rc="$2";
    log_message "[$rc] $msg" "ERROR"
    exit $rc
}

function clieaa_command() {
    if [ "$DEBUG" == "1" ]; then
        export CLIEAA_DEBUG="${DEBUG}"
        log_message "#### DEBUG MODE ####"
        CLI_EAA_CMD=/Users/androcho/github/cli-eaa/bin/akamai-eaa-venv
        log_message "Using cli-eaa: ${CLI_EAA_CMD}"
        log_message "####################"
    else
        echo "akamai eaa"
    fi
}