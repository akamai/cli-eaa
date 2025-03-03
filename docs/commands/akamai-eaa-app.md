[< cli-eaa documentation](../../README.md)

# akamai eaa app<!-- omit in toc -->

Manage EAA application configurations

Alias: `a`

## Table of contents<!-- omit in toc -->

- [Find and save an application](#find-and-save-an-application)
- [Restore the application](#restore-the-application)
- [Delete an application](#delete-an-application)
- [Create an new application configuration](#create-an-new-application-configuration)
  - [Basic](#basic)
  - [Variables and functions in the JSON configuration file](#variables-and-functions-in-the-json-configuration-file)
  - [Configuration templating](#configuration-templating)
- [Functions \& variables](#functions--variables)
  - [Functions](#functions)
    - [include(path\_to\_file)](#includepath_to_file)
    - [cli\_certificate(common\_name)](#cli_certificatecommon_name)
    - [cli\_cloudzone(cloudzone\_name)](#cli_cloudzonecloudzone_name)
  - [Enumeration variables](#enumeration-variables)
    - [AppProfile](#appprofile)
    - [AppType](#apptype)
    - [AppDomainType](#appdomaintype)


## Find and save an application

```
$ akamai eaa search datascience
app://●●●●●●●●●●●●●●●●●●●●●●,Data Science,akdemo-datascience,akdemo-datascience.go.akamai-access.com,4
Found 1 app(s), total 124 app(s)
```
Save an application:
You can save the application locally:
```
$ akamai eaa app app://●●●●●●●●●●●●●●●●●●●●●● > ~/eaa_app_datascience_v3.json
```

Quickly walk through the JSON tree using `jq`.

```bash
$ akamai eaa -b app app://●●●●●●●●●●●●●●●●●●●●●● | jq .advanced_settings.websocket_enabled
"true"
```


## Restore the application

Use the `update` keyword.

```
$ cat ~/eaa_app_datascience_v3.json | akamai eaa app app://mD_Pw1XASpyVJc2JwgICTg update
```

## Delete an application

```
$ akamai eaa app app://●●●●●●●●●●●●●●●●●●●●●● delete
```

Deploy an application, you can optionally add a comment to keep track of the change:
```
$ akamai eaa app app://●●●●●●●●●●●●●●●●●●●●●● deploy --comment "[TICKET1234] Update service account credentials"
```

Finding an application using a specific connector name: 
*What are the applications using connector `xyz`?*\
Use `jq` and `grep`.\
Note: we use `-b` to avoid the extra info the CLI spills out, like the footer.

```
$ akamai eaa -b search | akamai eaa app - | jq -j '.name, ": ", (.agents[]|.name, " "), "\n"'|grep xyz
```

View groups associated with a particular application:
```
$ akamai eaa app app://●●●●●●●●●●●●●●●●●●●●●● viewgroups
```

You can pipe the command as well, for example to deploy all the application matching your search (eg. "bastion")

```
$ akamai eaa -b search bastion | akamai eaa app - deploy
```

Attach/detach connectors to a particular application:

```
$ akamai eaa app app://app-uuid-1 attach con://connector-uuid-1 con://connector-uuid-2
$ akamai eaa app app://app-uuid-1 detach con://connector-uuid-1 con://connector-uuid-2
```

## Create an new application configuration

### Basic

You need to pass the application configuration JSON to the CLI using a pipe.

```
$ cat your-new-app.json | akamai eaa app - create
```

### Variables and functions in the JSON configuration file

You can use variables and functions inside the JSON file thanks
to the Jinja templating engine.

Read more about [Jinja][(https://jinja.palletsprojects.com/en/3.1.x/](https://jinja.palletsprojects.com/en/latest/)).

Variables can be set within the JSON file, or externally using 
`--var <var_name> <var_value>` argument after the `create`.

Example `cat webapp.json.j2 | akamai eaa app create --var MYVARIABLE VALUE` will allow to use DUMMY inside the code: `{{ MYVARIABLE }}`.

<details>
<summary>Example of an EAA configuration with variables and functions:</summary>

```jinja
{
    "eaa_cli_comment": [
        "This is an example of JSON with variables/functions",
        "to create an application with CLI-EAA",
	    "To create the app, use the following command:",
        "cat this_file.json.j2 | akamai eaa -v app - create"
    ],

    {# Pure Jinja variable #}
    {% set random_appsuffix = range(1, 10000) | random %}

    "app_profile": {{ AppProfile.HTTP.value }},
    "domain" : {{ AppDomainType.Custom.value }},
    "name": "EAA CLI Example Application Cust Domain {{ random_appsuffix }}",
    "description" : "Test app to be deleted",

    "advanced_settings": {
        "internal_hostname": "www.example.com",
        "internal_host_port": "0"
    },

    "cert":	"{{ cli_certificate('*.akamaidemo.net') }}",
    "host" : "dummyspopenapidelete{{ random_appsuffix }}.akamaidemo.net",
    "pop": "{{ cli_cloudzone('US-East') }}", 
    "servers": [
        {"origin_host": "www1.example.com", "orig_tls": "true", "origin_port": 80, "origin_protocol": "http"},
        {"origin_host": "www2.example.com", "orig_tls": "true", "origin_port": 81, "origin_protocol": "http"}
    ],
    "agents": [
        {"name": "demo-v2-con-1-amer", "uuid_url": "abc"},
        {"name": "demo-v2-con-2-amer", "uuid_url": "def"}
    ],
    "idp": {
    	"idp_id": "ghi"
    },
    "directories": [
       {
          "name": "AD Domain",
          "uuid_url": "jkl"
       }
    ],
    "groups": [
        {
          "name": "Administrators",
          "enable_mfa": "inherit",
          "uuid_url": "●●●●●●●●●●●●●●●●●●●●●●"
        },
        {
          "name": "Support",
          "enable_mfa": "inherit",
          "uuid_url": "●●●●●●●●●●●●●●●●●●●●●●"
        }
    ]
}
```
</details>

More example available in the [docs/examples](../examples/) directory.

### Configuration templating

Many parts of EAA configuration can be repeated accross multiple applications.
To save you time on generating the JSON files, you can use the Jinja2 templating.
Jinja is a templating engine adopted by tools like Ansible.

We recommend to start by saving locally a configuration you created with Akamai 
Control Center/Enterprise Center, and start splitting it into smaller file you include.

Templating is very powerful and you might run into syntax error. We recommend to use 
the `-d` option right after the `akamai eaa` command to troubleshoot.

## Functions & variables

### Functions

#### include(path_to_file) 

This is a Jinja Built-in function.

Anywhere in the JSON file, you can use the `include` function so the CLI
will find the included file and merge it into the main configuration before
passing it on to the EAA API.

The path will be relative to where the cli command is being executed.

Example:
```jinja
"idp": {% include 'includes/my-idp.json' %}
```

Where `includes/my-idp.json` will contain:
```json
{
    "client_cert_auth": "false",
    "client_cert_user_param": "",
    "dp_enabled": "true",
    "idp_id": "abcde",
    "name": "My IdP",
    "type": 2
}
```

#### cli_certificate(common_name)

Lookup the custom certification with corresponding common name (CN)
inside the EAA Custom Certificate Store.  
This will set the attribute/key `cert` of the application configuration.

#### cli_cloudzone(cloudzone_name)

Will return the cloudzone UUID.  
This will set the attribute/key `pop` of the application configuration.

### Enumeration variables

#### AppProfile

This is the string that indicate what type of application configuration (Web app, Tunnel App...).
The enum will set the attribute/key `app_profile` of the application configuration.

You must use the variable with `.value` to translate from human readable to an integer EAA API can understand:

```jinja
"app_profile": {{ AppProfile.HTTP.value }}
```

#### AppType

```jinja
"app_type": {{ AppType.Tunnel.value }}
```

#### AppDomainType

```jinja
"app_type": {{ AppDomainType.Akamai.value }}
```
