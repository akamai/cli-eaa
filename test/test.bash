#!/bin/bash
#
# Unit testing for cli-eaa
# Works on macOs and Linux OS
# Windows OS: not tested.

dir=$(cd .. && pwd -P)

echo "Starting akamai cli eaa tests..."

if [ "$1" == "cli" ]; then
    # Native Akamai CLI
    interpreter='akamai eaa -v'
else
    # For development purpose
    if type -t deactivate > /dev/null; then
        deactivate
    fi
    . $dir/venv/bin/activate
    interpreter="$dir/bin/akamai-eaa -v"
fi

echo "cli-eaa interpreter: $interpreter"

# Version

$interpreter version

# Logs 

$interpreter log access
$interpreter log admin

# Search

$interpreter search

# Directory operations

$interpreter dir list

##$interpreter dir://abcdef groups 
##$interpreter dir://abcdef users androcho
##$interpreter dir://abcdef add user://abcdef group:// 

# $interpreter idp "Global IdP" block "testblkuser1"

echo "Test completed."