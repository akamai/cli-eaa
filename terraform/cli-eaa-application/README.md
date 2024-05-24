# eaa-application terraform module

Terraform module allows to provision (create/update) or deprovision (delete) EAA application configuration in your Terraform code, relying on BASH and `cli-eaa`. 

It leverages Terraform `local-exec` provisioner which are "a Last Resort": keep this in mind.

For native EAA Terraform, we recommend https://github.com/akamai/terraform-eaa.

## Getting started

See [examples](examples/) sub-directory for details.

```HCL

module "my-eaa-app" {

    # You may pin a tagged version here, or use the lasted main branch
    source = "https://github.com/akamai/cli-eaa/terraform/cli-eaa-application"

    # API Credentials
    openapi_credentials = {
      access_token = "akab-abcd"
      client_secret = "abcdef"
      client_token = "akab-abcdef"
      hostname = "akab-abcdef.luna.akamaiapis.net"
    }

    # Authentication
    auth_idp_name = "MyIdP"
    auth_directory_name = "MyActiveDirectory"
    auth_group_names = ["MyGroup"]

    # Connectors
    connector_names = ["con-1", "con-2"]

    # Application info
    cloudzone_name = "Client-US-East"
    app_name = "My EAA application"
    app_description = " created with Terraform"
    tunnel_destination = {
        host_or_ip = "www.akamai.com"
        ports = "443"
    }

}
```

## Limitations

- Only one identity directory
- Only client-app type=tunnel
- Only Akamai external hostnames (.go.akamai-access.com)
