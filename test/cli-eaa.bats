#!/usr/bin/env bats

# see https://bats-core.readthedocs.io/

if [ "$SECTION" == "" ]; then
  SECTION="default"
fi

CLI="python3 ${BATS_TEST_DIRNAME}/../bin/akamai-eaa --section $SECTION"

setup() {
  echo "CLI: ${CLI}"
}

teardown() {
    echo "Clean up"
}

@test "version" {
  result="$(${CLI} version)"
  echo $result
  [ "$?" -eq 0 ]
}

# Help should print help and return code == 2
@test "help" {
  run ${CLI} help
  [ "$status" -eq 2 ]
}

@test "Search applications" {
  run ${CLI} search
  [ "$status" -eq 0 ]
}

@test "Create a tunnel application" {
  run bash createapp.bash ${CLI}
  [ "$status" -eq 0 ]
}

@test "Connector list" {
  run ${CLI} connector list
  [ "$status" -eq 0 ]
}

@test "User access logs" {
    run ${CLI} log access
  [ "$status" -eq 0 ]
}

@test "Audit logs" {
    run ${CLI} log admin
  [ "$status" -eq 0 ]
}

@test "Device Posture Inventory" {
  result="$(${CLI} dp inventory)"
  [ "$?" -eq 0 ]
}

@test "Device Posture Inventory (JSON)" {
  result="$(${CLI} dp inventory --json)"
  [ "$?" -eq 0 ]
}

@test "Certificates" {
  result="$(${CLI} cert)"
  [ "$?" -eq 0 ]
}

