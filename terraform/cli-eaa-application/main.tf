resource "null_resource" "eaa-application" {

  triggers = {

      # Application meta-data
      app_name = var.app_name
      app_description = var.app_description

      # Tunnel destination
      tunnel_destination_host_or_ip = var.tunnel_destination.host_or_ip
      tunnel_destination_ports = var.tunnel_destination.ports

      # Other configuration
      cloudzone_name = var.cloudzone_name
      auth_idp_name = var.auth_idp_name
      auth_group_names = join(",", var.auth_group_names)
      auth_directory_name = var.auth_directory_name
      connector_names = join(",", var.connector_names)

      # Misc
      clieaa_command = var.clieaa_command
      deploy = var.deploy ? 1 : 0
      log_file = var.log_file != null ? var.log_file : ""

      # API Credentials
      hostname = var.openapi_credentials.hostname
      client_secret = var.openapi_credentials.client_secret
      client_token = var.openapi_credentials.client_token
      access_token = var.openapi_credentials.access_token
      account_key = var.openapi_credentials.account_key != null ? var.openapi_credentials.account_key : ""

  }

  provisioner "local-exec" {
    when   = create
    interpreter = ["bash"]
    command = "${path.module}/scripts/provision.sh"
    environment = {
      CLIEAA_COMMAND=self.triggers.clieaa_command
      LOG_FILE=self.triggers.log_file
      APP_NAME=self.triggers.app_name
      APP_DESCRIPTION=self.triggers.app_description
      CLOUDZONE_NAME=self.triggers.cloudzone_name
      IDP_NAME=self.triggers.auth_idp_name
      DIRECTORY_NAME=self.triggers.auth_directory_name
      GROUP_NAMES=self.triggers.auth_group_names
      TUNNEL_DESTINATION_HOST_OR_IP=self.triggers.tunnel_destination_host_or_ip
      TUNNEL_DESTINATION_PORTS=self.triggers.tunnel_destination_ports
      CONNECTOR_NAMES=self.triggers.connector_names
      OPENAPI_HOST=self.triggers.hostname
      OPENAPI_CLIENT_SECRET=self.triggers.client_secret
      OPENAPI_CLIENT_TOKEN=self.triggers.client_token
      OPENAPI_ACCESS_TOKEN=self.triggers.access_token
      OPENAPI_ACCOUNT_KEY=self.triggers.account_key
      DEPLOY=self.triggers.deploy
    }
    # on_failure = continue
  }

  provisioner "local-exec" {
    when   = destroy
    interpreter = ["bash"]
    command = "${path.module}/scripts/deprovision.sh"
    environment = {
      CLIEAA_COMMAND=self.triggers.clieaa_command
      LOG_FILE=self.triggers.log_file
      APP_NAME=self.triggers.app_name
      OPENAPI_HOST=self.triggers.hostname
      OPENAPI_CLIENT_SECRET=self.triggers.client_secret
      OPENAPI_CLIENT_TOKEN=self.triggers.client_token
      OPENAPI_ACCESS_TOKEN=self.triggers.access_token
      OPENAPI_ACCOUNT_KEY=self.triggers.account_key
    }
    # on_failure = continue
  }

}