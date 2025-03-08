[< cli-eaa documentation](../../README.md)

# akamai eaa dp

Manage device posture inventory.  

You can export this data feed into your own SIEM with (Akamai Unified Log Streamer)[https://github.com/akamai/uls].

## View device inventory

Pipe the result of the inventory into `jq` to display only device ID, name and user_id:

```bash
$ akamai eaa dp inventory | jq '.[] | {device_id, device_name, user_id}'
```

## Watch (tail) the inventory

By default the cli will poll and print data every 10 minutes.
You can increase the interval by using the `--interval <interval-in-seconds>` argument.

```bash
$ akamai eaa dp inventory --tail
```

