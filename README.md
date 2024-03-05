# Akamai CLI: Enterprise Application Access<!-- omit in toc -->

## Table of contents<!-- omit in toc -->

- [Screenshot](#screenshot)
- [Introduction](#introduction)
- [Key features](#key-features)
- [Installation / upgrade](#installation--upgrade)
- [Examples](#examples)
  - [EAA Event Logs](#eaa-event-logs)
  - [Applications](#applications)
  - [Directory operations](#directory-operations)
  - [Connectors](#connectors)
  - [Certificate management](#certificate-management)
  - [Device Posture Inventory](#device-posture-inventory)
- [Known Limitations](#known-limitations)
- [Troubleshooting and Support](#troubleshooting-and-support)
  - [Self-troubleshooting](#self-troubleshooting)
  - [Support](#support)

## Screenshot

<img src="docs/cli-eaa-terminal@2x.png" width="40%" />

## Introduction

[Enterprise Application Access (EAA)](https://www.akamai.com/us/en/products/security/enterprise-application-access.jsp) comes with a full suite of APIs. 
To interact with the service, you can: 
- write scripts
- use [Postman](https://developer.akamai.com/authenticate-with-postman) 
- use [Akamai CLI](https://developer.akamai.com/cli) to run common operations directly from the command line, no coding required. 

This can be helpful if you plan to consume EAA logs into your favorite SIEM or automate your workflow with Bash, Powershell or a deployment solution like Ansible.

## Key features

- Event logs
  - View access logs (identification, application activity)
  - View admin logs (admin portal access, config change, deployment, deletion)
  - Send the logs to a file
  - Blocking mode (similar to `tail -f`) Alternatively, you can specify a date range with `--start` and `--end`
- Application
  - Save, restore/update, deploy
  - Batch operation
  - Attach/detach connectors
- Directory
  - Create groups and group overlays
  - Synchronize with your LDAP or Active Directory
- Identity Providers (IdP)
  - List configured IdPs and their status
- Certificate management
  - List configured certificates
  - Rotate certificate with optional deployment of dependent applications and IdP
- Connectors
  - List all connectors including the reachability status and health
  - Show all applications used by a connector and a breakdown of active connection
  - Swap a connector (for applications only)

## Installation / upgrade

See [install.md](docs/install.md)

## Examples

### EAA Event Logs

See [`akamai eaa log` documentation page](docs/commands/akamai-eaa-log.md)

### Applications

See [`akamai eaa app` documentation page](docs/commands/akamai-eaa-app.md). 

### Directory operations

See [`akamai eaa log` documentation page](docs/commands/akamai-eaa-dir.md)

### Connectors

See [`akamai eaa connector` documentation page](docs/commands/akamai-eaa-connector.md).

### Certificate management

See [`akamai eaa certificate` documentation page](docs/commands/akamai-eaa-certificate.md).

### Device Posture Inventory

See [`akamai eaa dp` documentation page](docs/commands/akamai-eaa-dp.md).

## Known Limitations

While updating an application from a JSON, only a subset of the data will be updated in the back-end, not the entire application configuration.

## Troubleshooting and Support

### Self-troubleshooting

If the command is not working properly, you can increase the level of verbosity using:

- `-v` or `--verbose` to trace the main steps
- `-d` or `--debug` to get full visibility, include API HTTP headers

The messages are printed on _stderr_ so you can safely redirect stdout to a file or use the `--output` option.

### Support

`cli-eaa` is provided as-is and it is not supported by Akamai Support.
To report any issue, feature request or bug, please open a new issue into the [GitHub Issues page](https://github.com/akamai/cli-eaa/issues)
We strongly encourage developers to create a pull request for any issues. 
