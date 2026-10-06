variable "project_id" {
  description = "Approved dedicated existing lab project."
  type        = string
}
variable "region" {
  description = "Approved region for retained state storage."
  type        = string
}
variable "state_bucket_name" {
  description = "Globally unique, public-safe name for private retained Terraform state."
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,61}[a-z0-9]$", var.state_bucket_name))
    error_message = "Provide a safe explicit bucket name."
  }
}
variable "approved_project_roles" {
  description = "Separately reviewed cloud apply roles. Empty grants state access only."
  type        = set(string)
  default     = []
  validation {
    condition     = alltrue([for role in var.approved_project_roles : startswith(role, "roles/") && !contains(["roles/owner", "roles/editor"], role)])
    error_message = "Use explicitly reviewed predefined roles; Owner and Editor are forbidden."
  }
}

variable "enable_cost_alerts" {
  description = "Create the project-scoped gross-cost budget and private email channel."
  type        = bool
  default     = false
}

variable "billing_account_id" {
  description = "Approved billing account for the project-scoped budget. Required when cost alerts are enabled."
  type        = string
  default     = ""
}

variable "cost_budget_currency" {
  description = "Must be GBP so the configured monthly gross budget enforces the approved £5 amount."
  type        = string
  default     = ""
}

variable "cost_budget_amount" {
  description = "Gross monthly budget in GBP; must be positive and no greater than £5."
  type        = number
  default     = 0
}

variable "cost_alert_email" {
  description = "Private recipient for project budget notifications; keep tfvars/state private."
  type        = string
  sensitive   = true
  default     = ""
}
