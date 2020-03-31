#!/bin/bash
#
# Unit testing for cli-eaa

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


echo "Test completed."