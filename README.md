# Akamai CLI: Enterprise Application Access

## Table of contents

<!-- TOC -->autoauto- [Akamai CLI: Enterprise Application Access](#akamai-cli-enterprise-application-access)auto    - [Table of contents](#table-of-contents)auto    - [Introduction](#introduction)auto    - [Feature highlight](#feature-highlight)auto    - [Installation](#installation)auto        - [Configuration file](#configuration-file)auto        - [Upgrade](#upgrade)auto    - [Fields documentation](#fields-documentation)auto    - [Examples](#examples)auto        - [Pull EAA logs](#pull-eaa-logs)auto    - [Troubleshooting](#troubleshooting)autoauto<!-- /TOC -->

## Introduction

[Enterprise Application Access (EAA)](https://www.akamai.com/us/en/products/security/enterprise-application-access.jsp) comes with a full suite of APIs. Yet you need to build scripts to be able to interact with the service.

With [Akamai CLI](https://developer.akamai.com/cli) you can run very common operations directly from the command line, no coding required. 

This can be particularly helpful if you plan to consume EAA logs into your favorite SIEM.

## Feature highlight

- View access logs (identification, application activity)
- View admin logs (admin portal access, config change, deployment, deletion)
- Send the logs to a file
- Blocking mode (similar to `tail -f`)
- Alternatively, you can specify a date range with `--start` and `--end`

## Installation

Make sure your first have the akamai CLI installed on your device.
For more information, please visit the [Getting Started](https://developer.akamai.com/cli/docs/getting-started) guide on developer.akamai.com.

Once the CLI is ready, EAA module installation is done via `akamai install` command:

```
$ akamai install eaa
```

The command takes care of all the dependencies. This CLI module uses Python in the background.

### Configuration file

In order to work, the CLI module will look for an `.edgerc` configuration file in the path or in your home directory.

The `.edgerc` file should look like:
```
[default]
eaa_api_host = manage.akamai-access.com
eaa_api_key = XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXXX
eaa_api_secret = XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXXX
```

You can obtain key and secret from your EAA administator, in **System** > **Settings** and then click **Generate new API Key** in the **API** section.

### Upgrade

To upgrade your CLI EAA module to the latest version, we recommend uninstall followed by install

```bash
$ akamai uninstall eaa
$ akamai install eaa
```
## Fields documentation

For detailed description about each field, please refer to the product documentation on https://learn.akamai.com.

## Examples

### Pull EAA logs

EAA has two types of logs, the user access logs and the administrators audit logs.
You can p   ull log either in near realtime, using `-f`, or retrieve a period of time passing EPOCH timestamp in `--start` and `--end`
You cannot combine `-f` and explicit date range.

Pull user access logs, block till new logs are received.
You can stop by pressing Control+C (Control+Break) or sending a signal SIG_INT or SIG_TERM to the process

```bash
$ akamai eaa log access -tail
```

You may want a one time chunk of log for a period of time, let's say the last 6 hours:

```bash
$ START=$(bc <<< "$(date +%s) - 6 * 60 * 60")
$ akamai eaa log access -s $START
```

Send the user access log to a file (utf-8 encoding is being used):
```bash
$ akamai eaa log access -tail -o /tmp/eaa_access.log
```

Pull admin audit logs, block till new logs are received
```bash
$ akamai eaa log admin -tail
```

## Troubleshooting

If the command is not working properly, you can increase the level of verbosity using:

- `-v` or `--verbose` to trace the main steps
- `-d` or `--debug` to get full visibility, include API HTTP headers

The messages are printed on _stderr_ so you can safely redirect stdout to a file or using the `--output` option.