[< cli-eaa documentation](../../README.md)

# akamai eaa report<!-- omit in toc -->

Manage EAA application configurations

Alias: `r`, `reports`

## Table of contents<!-- omit in toc -->

- [Users who connected successfully to EAA and their last access time](#users-who-connected-successfully-to-eaa-and-their-last-access-time)


## Users who connected successfully to EAA and their last access time

This command may take several minutes depending on the time range, and activity on the IdP.  
Tenant with Client-based application will typically have more events and longer time to process.

It is a good idea to grab the *idp hostname* with the command:

```
$ akamai eaa idp  | column -s, -t          
#IdP-id                       name        idp_hostname               status    certificate                   client  dp
idp://yb_XndD-RjmCFTrTx1QGhw  AMEAADEMO   welcome.akamaidemo.net     Deployed  crt://XtH1dUwqS0qAztk0Zl_M6w  N       N
idp://_unBFxtJRbS4gZ8pz2ZLDA  OKTA        login-okta.akamaidemo.net  Deployed  crt://XtH1dUwqS0qAztk0Zl_M6w  Y       N
idp://NMmW2cwqQJanYn3VTXoS9Q  Global IdP  login.akamaidemo.net       Deployed  crt://XtH1dUwqS0qAztk0Zl_M6w  Y       N
idp://TRmwtYFHRqi9BDXlkvzceg  ADFS        login-adfs.akamaidemo.net  Deployed  crt://XtH1dUwqS0qAztk0Zl_M6w  N       N
```

From there, generate the report with the `-a` parameter:

```
$ akamai eaa report last_access -a login.akamaidemo.net > report_unique_users.csv
Range start: 1716850539 2024-05-27 15:55:39
Range end: 1717455339 2024-06-03 15:55:39
11 users accessed the application for this time range, 193 records processed
1 API calls issued.

$ head report_unique_users.csv
userid,last_access_epoch_ms,last_access_iso8601
engineering,1716993722339,2024-05-29T14:42:02.339000+00:00Z
it,1717141602759,2024-05-31T07:46:42.759000+00:00Z
sales,1716883434605,2024-05-28T08:03:54.605000+00:00Z
```