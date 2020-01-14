# Akamai CLI: Enterprise Application Access

## Scope

Enterprise Application Access (EAA) comes with a full suite of APIs. 
Yet you need to build scripts to be able to interact with the service.

With Akamai CLI you can run very common operations directly from the command line, no coding required. 

This can be particularly helpful if you plan to consume EAA logs into your favorite SIEM.

## Feature highlight

- View access logs (identification, application activity)
- View admin logs (admin portal access, config change, deployment, deletion)
- Send the logs to a file
- Blocking mode (similar to `tail -f`)
- Alternatively, you can specify a date range with `--start` and `--end`

## Installation

Installation is done via `akamai install` command:

```
$ akamai install eaa
```

The command takes care of all the dependencies. This CLI module uses Python in the background.

### EAA API keys

In order to work, the CLI module will look for an `.edgerc` file in the path or in your home directory.

The `.edgerc` file should look like:
```
[default]
eaa_api_host = manage.akamai-access.com
eaa_api_key = XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXXX
eaa_api_secret = XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXXX
```

You can obtain key and secret from your EAA administator, in **System** > **Settings** and then click **Generate new API Key** in the **API** section.

## Examples

### Pull EAA logs

Pull user access logs, block till new logs are received
```
$ akamai eaa log access -tail
```

Send the access log to a file (utf-8 encoding is being used):
```
$ akamai eaa log access -tail -o /tmp/eaa_access.log
```

Pull admin logs, block till new logs are received
```
$ akamai eaa log admin -tail
```