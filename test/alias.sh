#!/bin/bash
# Override any existing production akamai CLI in favor
# of the local eaa

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

akamai () {
    if (( "$#" == 0 )); then
        echo "This is an Akamai CLI eaa wrapper."
        echo "Type:"
        echo "akamai eaa command ..."
        return
    fi
    subcommand=$1; shift # Pop the extreanous "eaa" arguments
    command ${SCRIPT_DIR}/../bin/akamai-eaa "$subcommand" "$@"
}

deakamai () {
    unset -f akamai
    unset -f deakamai
}