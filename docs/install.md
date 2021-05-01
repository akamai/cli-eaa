# Akamai CLI EAA module: installation and configuration instructions<!-- omit in toc -->

## Table of contents<!-- omit in toc -->

- [Installation](#installation)
  - [Pre-requisites](#pre-requisites)
  - [Akamai CLI](#akamai-cli)
  - [CLI EAA](#cli-eaa)
- [Configuration](#configuration)
- [Upgrade cli-eaa](#upgrade-cli-eaa)

## Installation

### Pre-requisites

Beyond Akamai CLI pre-requesites, cli-eaa requires Python 3.6 or greater on your system, as well as `pip`.

You can verify by opening a shell and type `python --version` and `pip --version`
If you don't have Python on your system, go to [https://www.python.org](https://www.python.org).

### Akamai CLI

Make sure your first have Akamai CLI installed on your machine.

We support a wide variety of platform: Windows, Mac, Linux, container...
Download the CLI from [https://developer.akamai.com/cli](https://developer.akamai.com/cli)

For more information, please visit the [Getting Started](https://developer.akamai.com/cli/docs/getting-started) guide on developer.akamai.com.

### CLI EAA

Once the Akamai CLI is installed, the `cli-eaa` module installation is done via `akamai install eaa` command:

```
$ akamai install eaa
```

And voilà!

The command takes care of all the dependencies. 

To check your cli-eaa version with the `version` command

```
$ akamai eaa version
0.3.2
```

## Configuration

In order to work, the CLI module will look for an `.edgerc` configuration file stored 
in your home directory or your prefered location. \
For the latter make sure to use the `--edgerc` parameter in the command line.\

To create a {OPEN} API user, follow [these instructions](https://developer.akamai.com/legacy/introduction/Prov_Creds.html).
Make sure the API user has READ-WRITE permission to *Enterprise Application Access*.

To create a legacy API key and secret from, connect to Akamai Control Center. 
- use Enterprise Application Access in the left menu
- go to **System** > **Settings** and 
- then click **Generate new API Key** in the **API** section of the page

The `.edgerc` file should look like:

```INI
[default]

; EAA Legacy API used by the 'akamai eaa log' command
eaa_api_host = manage.akamai-access.com
eaa_api_key = XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXXX
eaa_api_secret = XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXXX

; {OPEN} API for everything else
host = akaa-xxxxxxxxxxxxxxxx-xxxxxxxxxxxxxxxx.luna.akamaiapis.net
client_token = akab-xxxxxxxxxxxxxxxx-xxxxxxxxxxxxxxxx
client_secret = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
access_token = akab-xxxxxxxxxxxxxxxx-xxxxxxxxxxxxxxxx
; If your organization have multiple contracts with EAA service
; please add it below. Contact your Akamai representative to obtain it
contract_id = A-B-1CD2E34
; If you are a partner managing multiple customers, you can use the switchkey
; For more information, see:
; https://learn.akamai.com/en-us/learn_akamai/getting_started_with_akamai_developers/developer_tools/accountSwitch.html
extra_qs = accountSwitchKey=TENANT-SWITCH-KEY
```

## Upgrade cli-eaa

To upgrade your CLI EAA module to the latest version, use:

```bash
$ akamai update eaa
```

Verify the version

```bash
$ akamai eaa version
```
