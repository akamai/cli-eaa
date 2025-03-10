[< cli-eaa documentation](../../README.md)

# akamai eaa directory

Manage Akamai EAA directory configurations.

Alias: `dir`

## List the configured directories

```
$ akamai eaa dir
dir://●●●●●●●●●●●●●●●●●●●●●●,Cloud Directory,7
dir://●●●●●●●●●●●●●●●●●●●●●●,ad.akamaidemo.net,108
dir://●●●●●●●●●●●●●●●●●●●●●●,Okta LDAP,10
dir://●●●●●●●●●●●●●●●●●●●●●●,Azure AD,1
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
$ akamai eaa dir dir://●●●●●●●●●●●●●●●●●●●●●● sync
Synchronize directory ●●●●●●●●●●●●●●●●●●●●●●
Directory ●●●●●●●●●●●●●●●●●●●●●● synchronization requested.
```