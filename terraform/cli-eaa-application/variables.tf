variable "app_name" {
  type = string
  description = "Friendly name of the application"
}

variable "app_description" {
  type = string
  description = "Description the application"
}

variable "auth_idp_name" {
    type = string
    description = "IdP Hostname to attach the app to"
} 

variable "auth_directory_name" {
    type = string
    description = "Name of the directory"
} 

variable "auth_group_names" {
    type = list(string)
    description = "List of group allowed to access the application"
}

variable "tunnel_destination" {
    description = "Client-app destination and port"
    type = object({
        host_or_ip = string
        ports = string
    })
}

variable "connector_names" {
    type = list(string)
    description = "List of connector names to attach to the application"
    validation {
      condition = length(var.connector_names) > 0
      error_message = "An EAA application configuration need to be attached to at least one EAA connector, ${length(var.connector_names)} provided."
    }
}

variable "cloudzone_name" {
    type = string
    description = "Cloudzone name, use 'akamai eaa info' to see the available name in your tenant"
}

variable "openapi_credentials" {
    # sensitive = true
    description = "OpenAPI credentials with READ/WRITE permission on EAA"
    type = object({
        hostname = string
        client_secret = string
        client_token = string
        access_token = string
        account_key = optional(string)
    })
}

variable "deploy" {
    default = false
    type = bool
    description = "Deploy after creation/update" 
}

variable "log_file" {
    type = string
    default = null
    description = "Log file of the create/delete EAA Application configuration (default=null)"
}

variable "clieaa_command" {
    type = string
    default = "akamai eaa"
    description = "Akamai EAA command, leave default unless troubleshooting/developer. See https://github.com/akamai/cli for more details"
}
