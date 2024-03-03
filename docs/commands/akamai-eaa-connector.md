[< cli-eaa documentation](../../README.md)

# akamai eaa connector<!-- omit in toc -->

Aliases: `c`, `con`

Display list of connectors and their status.

## Table of contents<!-- omit in toc -->

- [Usage](#usage)
- [List all EAA connectors](#list-all-eaa-connectors)
- [Swapping connectors](#swapping-connectors)
- [Show connector outbound allowlist IP/CIDR or hostnames](#show-connector-outbound-allowlist-ipcidr-or-hostnames)

## Usage

```
% akamai eaa connector -h
usage: akamai eaa connector [-h] [connector_id] {apps,list,swap,allowlist} ...

positional arguments:
  connector_id          Connector ID (e.g. con://abcdefghi)
  {apps,list,swap,allowlist} Connector operation:
    apps                List applications used by the connector
    list                List all connectors
    swap                Swap connector with another one
    allowlist           Dump EAA Cloud Endpoint for Firewall/
                        Proxy/Network Security equipement
```

Tips:
- pipe CLI output `column` tool available in most POSIX environment.
- when piping, the extra information is written to *stderr* so they appear seperately.

## List all EAA connectors

This example shows a short command `akamai eaa c`, replacing `akamai eaa connector list`:

```
$ akamai eaa c | column -t -s,
Total 9 connector(s)
#Connector-id                 name                reachable  status  version     privateip      publicip        debug
con://cht3_GEjQWyMW9LEk7KQfg  demo-v2-con-1-amer  1          1       4.4.0-2765  10.1.4.206     12.123.123.123  Y
con://Wy0Y6FrwQ66yQzLBAInC4w  demo-v2-con-2-amer  1          1       4.4.0-2765  10.1.4.172     12.123.123.123  Y
con://dK0f1UvhR7i8-RByABDXaQ  demo-v2-con-4-emea  1          1       4.4.0-2765  192.168.1.90   12.123.12.12    N
con://Ihmf51dASo-R1P37hzaP3Q  demo-v2-con-3-emea  1          1       4.4.0-2765  192.168.1.235  12.123.12.12    N
con://XiCmu80xQcSWnaeQcvH8Vg  demo-v2-con-5-apj   1          1       4.4.0-2765  192.168.1.228  12.123.123.12   Y
con://pkGjL5OgSjyHoymMguvp9Q  demo-v2-con-6-apj   1          1       4.4.0-2765  192.168.1.144  12.123.123.12   Y
con://NAWSlptPSXOjq-bk2-EQPw  demo-v2-con-10-rus  1          1       4.4.0-2765  10.3.0.101     12.123.123.12   Y
con://e_0nShZBQ7esNAC3ZEkhSQ  demo-v2-con-3-amer  1          1       4.4.0-2765  10.1.4.83      12.123.123.123  Y
con://OEe9o-n2S_aMeZpLxgwG0A  tmelab-sfo          1          1       4.4.0-2765  192.168.2.101  12.123.123.12   Y
```

To integrate connector health into your monitoring system, use the `--perf` option.
`akamai eaa c list --perf`
This provides 7 extra columns:
- CPU usage (%)
- Memory usage (%)
- Network Traffic (Mbps)
- Total of dialout connections
- Idle dialout connections
- Active dialout connections

To correlate with applications served by each connector, use the `--showapps` argument to include a list of the application FQDNs as an array in the JSON response.

## Swapping connectors

If you are doing a maintenance on an hypervizor, you may need to swap out 2 connectors.
The current implement look for all the apps, add the new connector, remove the old one.
The application is marked as ready to update.

Caveats (let us know if you need it):
- This doesn't perform swap for directory
- There is no option to automatically redeploy the impacted application after the swap

Example:
```
$ akamai eaa connector con://e_0nShZBQ7esNAC3ZEkhSQ swap con://cht3_GEjQWyMW9LEk7KQfg
#Operation,connector-id,connector-name,app-id,app-name
+,con://cht3_GEjQWyMW9LEk7KQfg,demo-v2-con-1-amer,app://nSFDNGYARHeZGNlweIX7Wg,Speedtest (v2.1)
-,con://e_0nShZBQ7esNAC3ZEkhSQ,demo-v2-con-3-amer,app://nSFDNGYARHeZGNlweIX7Wg,Speedtest (v2.1)
Connector swapped in 1 application(s).
Updated application(s) is/are marked as ready to deploy
```

## Show connector outbound allowlist IP/CIDR or hostnames

```
% akamai eaa connector allowlist
```