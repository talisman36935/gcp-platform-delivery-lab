output "workload_identity_provider" {
  value = google_iam_workload_identity_pool_provider.github.name
}
output "ci_service_account" {
  value = google_service_account.ci.email
}
output "state_bucket" {
  value = google_storage_bucket.state.name
}
output "backend_contract" {
  value = {
    bucket            = google_storage_bucket.state.name
    bootstrap_prefix  = "bootstrap"
    lab_prefix        = "lab"
    retained          = true
    cloud_roles_empty = length(var.approved_project_roles) == 0
  }
}
