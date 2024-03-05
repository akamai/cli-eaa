[< cli-eaa documentation](../../README.md)

# akamai eaa directory

Manage Akamai EAA directory configurations.

Alias: `dir`

## List the configured directories

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

## Trigger directory synchronization

```
$ akamai eaa dir dir://2Kz2YqmgSpqT_IJq9BLkWg sync
Synchronize directory 2Kz2YqmgSpqT_IJq9BLkWg
Directory 2Kz2YqmgSpqT_IJq9BLkWg synchronization requested.
```