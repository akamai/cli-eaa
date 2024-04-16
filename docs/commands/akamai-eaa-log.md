[< cli-eaa documentation](../../README.md)

# akamai eaa log<!-- omit in toc -->

Access to EAA security events and logs.

Alias: `l`

## Table of contents<!-- omit in toc -->

- [Command description](#command-description)
- [View access log in tail mode](#view-access-log-in-tail-mode)
- [View access log with specific date/time boundaries](#view-access-log-with-specific-datetime-boundaries)
- [Send access logs to a file](#send-access-logs-to-a-file)
- [Audit logs](#audit-logs)

## Command description

EAA comes with two types of logs, the user access logs and the administrator audit logs.
For detailed description for each event field, refer to the product documentation on [https://techdocs.akamai.com](https://techdocs.akamai.com/eaa/docs/data-feed-siem).

You can retrieve EAA events one of these ways:
- in near realtime using the argument `-f` or `--tail`. If you set `-f` and date range, the `-f` option will be ignored.
- retrieve a period of time based on EPOCH timestamp in `--start` and `--end`
- tune the acceptable delay vs. completeness with `--delay`. We recommend 10 minutes delay for full completeness.

You can also export this data feed into your own SIEM with (Akamai Unified Log Streamer)[https://github.com/akamai/uls].

## View access log in tail mode

Pull user access logs, block until new logs are received.
You can stop using Control+C (Control+Break) or sending a SIG_INT or SIG_TERM signal to the process.

```bash
$ akamai eaa log access --tail
```

## View access log with specific date/time boundaries

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

## Send access logs to a file

Send the **user access events** to a file (utf-8 encoding is being used):
```bash
$ akamai eaa log access --tail -o /tmp/eaa_access.log
```

## Audit logs

Pull **admin audit events**, block till new logs are received
```bash
$ akamai eaa log admin --tail
```
