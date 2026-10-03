variable "project_id" {
  description = "Dedicated existing, billing-enabled lab project. No shared production project."
  type        = string
}
variable "region" {
  description = "Explicit approved GCP region."
  type        = string
}
variable "zone" {
  description = "Single lab zone within region; not an HA configuration."
  type        = string
}
variable "operator_cidr" {
  description = "Approved operator egress IPv4 CIDR for the Kubernetes API."
  type        = string
  validation {
    condition     = can(cidrnetmask(var.operator_cidr)) && !endswith(var.operator_cidr, "/0")
    error_message = "Provide a restricted IPv4 CIDR; /0 is forbidden."
  }
}
variable "config_sync_version" {
  description = "Explicit supported Config Sync version qualified before a cloud run."
  type        = string
}
variable "source_revision" {
  description = "Reviewed 40-character Git commit for the root configuration."
  type        = string
  validation {
    condition     = can(regex("^[0-9a-f]{40}$", var.source_revision))
    error_message = "Pin an immutable Git commit."
  }
}
variable "deletion_protection" {
  description = "Disable deliberately in a reviewed teardown change, never as a default."
  type        = bool
  default     = true
}
