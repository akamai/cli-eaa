# Adjust this to match your EAA IdP, directory, groups

module "my-eaa-app" {

    source = "./../.."

    # API Credentials
    openapi_credentials = {
      access_token = "akab-abcd"
      client_secret = "abcdef"
      client_token = "akab-abcdef"
      hostname = "akab-abcdef.luna.akamaiapis.net"
    }

    # Authentication
    auth_idp_name = "My IdP"
    auth_directory_name = "My AD"
    auth_group_names = ["My group", "Other group"]

    # Connectors
    connector_names = [ "con-1", "con-2" ]

    # Application info
    cloudzone_name = "Client-US-East"
    app_name = "My example EAA application"
    app_description = "created with Terraform"
    tunnel_destination = {
        host_or_ip = "www.google.com"
        ports = "443"
    }

    clieaa_command = var.clieaa_command
    log_file = "cli-eaa-application.log"

}