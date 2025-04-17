[< cli-eaa documentation](../../README.md)

# akamai eaa connector<!-- omit in toc -->

Aliases: `c`, `con`

Display list of connectors and their status.

## Table of contents<!-- omit in toc -->

- [Usage](#usage)
- [List all EAA connectors](#list-all-eaa-connectors)
- [Swapping connectors](#swapping-connectors)
- [Show connector outbound allowlist IP/CIDR or hostnames](#show-connector-outbound-allowlist-ipcidr-or-hostnames)
- [Create a new connector](#create-a-new-connector)
- [Troubleshoot/debug Connector connectivity to behind-the-firewall network](#troubleshootdebug-connector-connectivity-to-behind-the-firewall-network)
  - [dig](#dig)
  - [ping](#ping)
  - [traceroute](#traceroute)
  - [lft](#lft)
  - [curl](#curl)

## Usage

```
% akamai eaa connector -h
usage: akamai eaa connector [-h] [connector_id] {apps,list,swap,remove,rm,create,allowlist} ...

positional arguments:
  connector_id          Connector ID (e.g. con://abcdefghi)
  {apps,list,swap,remove,rm,create,allowlist}
                        Connector operation
    apps                List applications used by the connector
    list                List all connectors
    swap                Swap connector with another one
    remove (rm)         Unregister a connector
    create              Create a new EAA connector
    allowlist           Dump EAA Cloud Endpoint for Firewall/Proxy/Network Security equipement

options:
  -h, --help            show this help message and exit
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
con://●●●●●●●●●●●●●●●●●●●●●●  demo-v2-con-1-amer  1          1       4.4.0-2765  10.1.4.206     12.123.123.123  Y
con://●●●●●●●●●●●●●●●●●●●●●●  demo-v2-con-2-amer  1          1       4.4.0-2765  10.1.4.172     12.123.123.123  Y
con://●●●●●●●●●●●●●●●●●●●●●●  demo-v2-con-4-emea  1          1       4.4.0-2765  192.168.1.90   12.123.12.12    N
con://●●●●●●●●●●●●●●●●●●●●●●  demo-v2-con-3-emea  1          1       4.4.0-2765  192.168.1.235  12.123.12.12    N
con://●●●●●●●●●●●●●●●●●●●●●●  demo-v2-con-5-apj   1          1       4.4.0-2765  192.168.1.228  12.123.123.12   Y
con://●●●●●●●●●●●●●●●●●●●●●●  demo-v2-con-6-apj   1          1       4.4.0-2765  192.168.1.144  12.123.123.12   Y
con://●●●●●●●●●●●●●●●●●●●●●●  demo-v2-con-10-rus  1          1       4.4.0-2765  10.3.0.101     12.123.123.12   Y
con://●●●●●●●●●●●●●●●●●●●●●●  demo-v2-con-3-amer  1          1       4.4.0-2765  10.1.4.83      12.123.123.123  Y
con://●●●●●●●●●●●●●●●●●●●●●●  tmelab-sfo          1          1       4.4.0-2765  192.168.2.101  12.123.123.12   Y
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
$ akamai eaa connector con://●●●●●●●●●●●●●●●●●●●●●● swap con://●●●●●●●●●●●●●●●●●●●●●●
#Operation,connector-id,connector-name,app-id,app-name
+,con://●●●●●●●●●●●●●●●●●●●●●●,demo-v2-con-1-amer,app://●●●●●●●●●●●●●●●●●●●●●●,Speedtest (v2.1)
-,con://●●●●●●●●●●●●●●●●●●●●●●,demo-v2-con-3-amer,app://●●●●●●●●●●●●●●●●●●●●●●,Speedtest (v2.1)
Connector swapped in 1 application(s).
Updated application(s) is/are marked as ready to deploy
```

## Show connector outbound allowlist IP/CIDR or hostnames

By default the command will generate a CSV on stdout with the following fields:
- Service name
- Location
- Protocol/Port
- IP/CIDR
- Last time the item was added/updated (RFC 3339)
- Number of apps consuming the Data Path + Location, requires `--used`

The first row is the CSV header

If `--fqdn` is used, will display only the hostname (some may come with wildcard) for Layer-7 capable security equipement such as HTTPS/TLS web proxies.

List of Akamai Cloud Service Endpoints by IP/CIDR
```
% akamai eaa connector allowlist
```

List of Akamai Cloud Service Endpoints by hostnames

```
% akamai eaa connector allowlist --fqdn
```

## Create a new connector

The command below will create a new connector for Docker and wait a maximum 
of 10 minutes to get the download URL. The response will be a JSON doc.
The `download_url` attribute MUST BE tested as it can be `null` even with 
the `--wait` option.

```
% akamai eaa create --name MyNewConnector --package Docker --debug --wait 600
```

## Troubleshoot/debug Connector connectivity to behind-the-firewall network

In Akamai Control Center, you can use tools such as
`ping` or `traceroute` to troubleshoot the connectivity between the
EAA connector and the other components it can reach.

Debug command may write output to `stdout` and/or `stderr` which is passed through.  
Debug command return code is passthrough although be aware not all tools returns
great than zero value in case of failure.

### dig

```
% akamai eaa connector con://●●●●●●●●●●●●●●●●●●●●●● debug --command dig --arguments www.akamai.com

; <<>> DiG 9.18.12-0ubuntu0.22.04.1-Ubuntu <<>> www.akamai.com
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 27798
;; flags: qr rd ra; QUERY: 1, ANSWER: 2, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 1232
;; QUESTION SECTION:
;www.akamai.com.                        IN      A

;; ANSWER SECTION:
www.akamai.com.         19      IN      A       23.12.147.13
www.akamai.com.         19      IN      A       23.12.147.29

;; Query time: 8 msec
;; SERVER: 127.0.0.1#53(127.0.0.1) (UDP)
;; WHEN: Thu Apr 17 20:32:25 UTC 2025
;; MSG SIZE  rcvd: 75
```

### ping

```
% akamai eaa connector con://●●●●●●●●●●●●●●●●●●●●●● debug --command ping --arguments www.akamai.com
PING www.akamai.com (23.12.147.29) 56(84) bytes of data.
64 bytes from a23-12-147-29.deploy.static.akamaitechnologies.com (23.12.147.29): icmp_seq=1 ttl=51 time=3.68 ms
64 bytes from a23-12-147-29.deploy.static.akamaitechnologies.com (23.12.147.29): icmp_seq=2 ttl=51 time=1.53 ms
64 bytes from a23-12-147-29.deploy.static.akamaitechnologies.com (23.12.147.29): icmp_seq=3 ttl=51 time=1.54 ms
64 bytes from a23-12-147-29.deploy.static.akamaitechnologies.com (23.12.147.29): icmp_seq=4 ttl=51 time=1.62 ms
64 bytes from a23-12-147-29.deploy.static.akamaitechnologies.com (23.12.147.29): icmp_seq=5 ttl=51 time=1.57 ms
64 bytes from a23-12-147-29.deploy.static.akamaitechnologies.com (23.12.147.29): icmp_seq=6 ttl=51 time=1.65 ms

--- www.akamai.com ping statistics ---
6 packets transmitted, 6 received, 0% packet loss, time 5007ms
rtt min/avg/max/mdev = 1.529/1.929/3.677/0.782 ms
```

### traceroute

```
% akamai eaa connector con://●●●●●●●●●●●●●●●●●●●●●● debug --command traceroute --arguments www.akamai.com
traceroute to www.akamai.com (23.12.147.156), 30 hops max, 60 byte packets
 1  10.1.3.76 (10.1.3.76)  0.852 ms  0.834 ms  1.047 ms
 2  * * *
 3  * * *
 4  * * *
 5  * * *
 6  * * *
 7  * * *
 8  * * *
 9  * * *
10  * * *
11  * * *
12  a23-12-147-156.deploy.static.akamaitechnologies.com (23.12.147.156)  3.659 ms  4.113 ms  3.192 ms
```

### lft

```
% akamai eaa connector con://●●●●●●●●●●●●●●●●●●●●●● debug --command lft --arguments www.akamai.com:80
Tracing ......**T
TTL LFT trace to a72-247-●●●-●●●.deploy.static.akamaitechnologies.com (72.247.●●●.●●●):80/tcp
 1  10.1.3.76 1.0ms
 2  240.3.●●●.●●● 3.5ms
 3  151.148.●●●.●●● 2.8ms
 4  151.148.●●●.●●● 2.6ms
**  [neglected] no reply packets received from TTL 5
 6  ●●●.●●●.●●●●●.●●●.netarch.akamai.com (23.209.●●●.●●●) 3.2ms
**  [neglected] no reply packets received from TTL 7
 8  [target open] a72-247-●●●-●●●.deploy.static.akamaitechnologies.com (72.247.●●●.●●●):80 3.5ms
```

### curl

```
% akamai eaa connector con://●●●●●●●●●●●●●●●●●●●●●● debug --command curl --arguments http://whatismyip.akamai.com
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0*   Trying 104.117.182.11:80...
* Connected to whatismyip.akamai.com (104.117.182.11) port 80 (#0)
> GET / HTTP/1.1
> Host: whatismyip.akamai.com
> User-Agent: curl/7.81.0
> Accept: */*
> Accept-Charset: ISO-8859-1,utf-8;
> 
* Mark bundle as not supporting multiuse
< HTTP/1.1 200 OK
< Content-Type: text/html
< Content-Length: 14
< Expires: Thu, 17 Apr 2025 20:27:34 GMT
< Cache-Control: max-age=0, no-cache, no-store
< Pragma: no-cache
< Date: Thu, 17 Apr 2025 20:27:34 GMT
< Connection: keep-alive
< 
{ [14 bytes data]
100    14  100    14    0     0    142      0 --:--:-- --:--:-- --:--:--   142
* Connection #0 to host whatismyip.akamai.com left intact
123.123.123.123
```

