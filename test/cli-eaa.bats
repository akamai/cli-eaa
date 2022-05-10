#!/usr/bin/env bats

CLI="python3 ${BATS_TEST_DIRNAME}/../bin/akamai-eaa"

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