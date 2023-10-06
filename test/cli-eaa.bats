#!/usr/bin/env bats

# see https://bats-core.readthedocs.io/

CLI="python3 ${BATS_TEST_DIRNAME}/../bin/akamai-eaa"
SCRIPT_DIR="$( cd "$( dirname "$BATS_TEST_FILENAME" )" >/dev/null 2>&1 && pwd )"
BASE_DIR="${SCRIPT_DIR}/.."

setup() {
  echo "CLI: ${CLI}"
  if [ -d "${BASE_DIR}/venv" ]; then
      echo "Detected Virtual Env directory: ${BASE_DIR}/venv, VIRTUAL_ENV=$VIRTUAL_ENV"
      if [ "$VIRTUAL_ENV" == "" ]; then
          echo "Activating VirtualEnv..."
          . ${BASE_DIR}/venv/bin/activate
          pip -q install --upgrade pip
          echo "Install/upgrade PIP packages as needed..."
          pip -q install --upgrade -r "${BASE_DIR}/requirements.txt"
      fi
  else
      echo "Virtual Env directory ${BASE_DIR}/venv missing"
      exit 2
  fi
}

teardown() {
    echo "Clean up"
}

@test "cli-eaa version" {
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

@test "Account informations" {
  result="$(${CLI} info)"
  [ "$?" -eq 0 ]
}

