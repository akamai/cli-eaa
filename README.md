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
    - [Display certificates](#display-certificates)
    - [Rotate certificates](#rotate-certificates)
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

EAA comes with two types of logs, the user access logs and the administrator audit logs.
For detailed description for each event field, refer to the product documentation on [https://techdocs.akamai.com](https://techdocs.akamai.com/eaa/docs/data-feed-siem).

You can retrieve EAA events one of these ways:
- in near realtime using the argument `-f` or `--tail`. If you set `-f` and date range, the `-f` option will be ignored.
- retrieve a period of time based on EPOCH timestamp in `--start` and `--end`
- tune the acceptable delay vs. completeness with `--delay`. We recommend 10 minutes delay for full completeness.

Pull user access logs, block until new logs are received.
You can stop using Control+C (Control+Break) or sending a SIG_INT or SIG_TERM signal to the process.

```bash
$ akamai eaa log access --tail
```

You may want a one time chunk of log for a period of time, for example, the last 6 hours:

```bash
$ START=$(bc <<< "$(date +%s) - 6 * 60 * 60")
$ akamai eaa log access -s $START
```

On Windows platforms, you can use PowerShell:
```powershell
PS /home/cli-eaa> $START = (Get-Date -UFormat %s) - 6 * 60 * 60
PS /home/cli-eaa> akamai eaa log access -s $START
```

Send the **user access events** to a file (utf-8 encoding is being used):
```bash
$ akamai eaa log access --tail -o /tmp/eaa_access.log
```

Pull **admin audit events**, block till new logs are received
```bash
$ akamai eaa log admin --tail
```

### Applications

See [akamai eaa command documentation page](docs/commands/akamai-eaa-app.md). 

### Directory operations

**List the configured directories**:

```
$ akamai eaa dir
dir://FuiibQiDQzmC34oBx7INfQ,Cloud Directory,7
dir://2Kz2YqmgSpqT_IJq9BLkWg,ad.akamaidemo.net,108
dir://EX5-YjMyTrKgeWKHrqhUEA,Okta LDAP,10
dir://Ygl1BpAFREiHrA8HR7dFhA,Azure AD,1
```

To view the output in JSON format and in follow mode to consume Directory Health:

```
$ akamai eaa dir list --json --tail | jq .name
"Cloud Directory"
"AD Domain AkamaiDemo.net (global)"
"Azure AD (Sync with SCIM)"
"AKDEMO AD with UPN"
```

**Trigger directory synchronization**

```
$ akamai eaa dir dir://2Kz2YqmgSpqT_IJq9BLkWg sync
Synchronize directory 2Kz2YqmgSpqT_IJq9BLkWg
Directory 2Kz2YqmgSpqT_IJq9BLkWg synchronization requested.
```

### Connectors

See [akamai eaa connectors](docs/commands/akamai-eaa-connector.md) command line doc and examples.

### Certificate management

#### Display certificates

The command `cert` displays all the certificate you have configured in EAA, along with the CN and SAN attribute in the `hosts` field, as a `+` separated list.

Example with a wildcard certificate:

```
$ akamai eaa cert | head -n1
#Certificate-ID,cn,type,expiration,days left,hosts
crt://KXi553saQSCeNI1_WH6xuA,*.akamaidemo.net,Custom,2031-06-05T22:56:34,3307,*.akamaidemo.net+akamaidemo.net
```

#### Rotate certificates

The cli-eaa helps with this task with the `akamai eaa certificate` command. 

Pass the certificate and key file as parameter with the optional passphrase to replace the existing certificate.
By default, the rotation does NOT redeploy the impacted application or IdP. 
To trigger the re-deployment of all impacted applications and IdP, add the ``--deployafter`` flag.

```
$ akamai eaa certificate crt://certificate-UUID rotate --key ~/certs/mycert.key --cert ~/certs/mycert.cert --deployafter
Rotating certificate certificate-UUID...
Certificate CN: *.akamaidemo.net (*.akamaidemo.net Lets Encrypt)
Certificate certificate-UUID updated, 3 application/IdP(s) have been marked ready for deployment.
Deploying application Multi-origin Active-Active Demo (US-East) (app://appid-1)...
Deploying application Multi-origin Active-Active Demo (US-West) (app://appid-2)...
Deploying IdP Bogus IdP to test EME-365 (idp://idpid-1)...
Deployment(s) in progress, it typically take 3 to 5 minutes
Use 'akamai eaa cert crt://certificate-UUID status' to monitor the progress.
```

Check the deployment status:

```bash
$ akamai eaa cert crt://certificate-UUID status
#App/IdP ID,name,status
app://appid-1,Multi-origin Active-Active Demo (US-East),Pending
app://appid-2,Multi-origin Active-Active Demo (US-West),Pending
idp://idpid-1,Bogus IdP to test EME-365,Pending
```

### Device Posture Inventory

Pipe the result of the inventory into `jq` to display only device ID, name and user_id:

```bash
$ akamai eaa dp inventory | jq '.[] | {device_id, device_name, user_id}'
```

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
