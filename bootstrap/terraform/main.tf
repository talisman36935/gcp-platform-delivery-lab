locals {
  repository_id = "1402116284"
  owner_id      = "68283664"
  workflow_ref  = "talisman36935/gcp-platform-delivery-lab/.github/workflows/cloud-run.yaml@refs/heads/main"
}

resource "google_project_service" "bootstrap" {
  for_each = toset([
    "iam.googleapis.com", "iamcredentials.googleapis.com",
    "sts.googleapis.com", "storage.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

resource "google_storage_bucket" "state" {
  name                        = var.state_bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  versioning { enabled = true }
  labels = {
    owner     = "portfolio-lab"
    lifecycle = "retained-bootstrap"
  }
  lifecycle { prevent_destroy = true }
  depends_on = [google_project_service.bootstrap]
}

resource "google_service_account" "ci" {
  account_id   = "portfolio-delivery-ci"
  display_name = "Scoped portfolio delivery workflow identity"
  depends_on   = [google_project_service.bootstrap]
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "portfolio-github"
  display_name              = "Portfolio GitHub federation"
  depends_on                = [google_project_service.bootstrap]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "delivery"
  attribute_mapping = {
    "google.subject"                = "assertion.sub"
    "attribute.repository_id"       = "assertion.repository_id"
    "attribute.repository_owner_id" = "assertion.repository_owner_id"
    "attribute.ref"                 = "assertion.ref"
    "attribute.workflow_ref"        = "assertion.workflow_ref"
    "attribute.event_name"          = "assertion.event_name"
  }
  attribute_condition = join(" && ", [
    "assertion.repository_id == '${local.repository_id}'",
    "assertion.repository_owner_id == '${local.owner_id}'",
    "assertion.ref == 'refs/heads/main'",
    "assertion.workflow_ref == '${local.workflow_ref}'",
    "assertion.event_name == 'workflow_dispatch'",
  ])
  oidc { issuer_uri = "https://token.actions.githubusercontent.com" }
}

resource "google_service_account_iam_member" "federation" {
  service_account_id = google_service_account.ci.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository_id/${local.repository_id}"
}

resource "google_storage_bucket_iam_member" "state_writer" {
  bucket = google_storage_bucket.state.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ci.email}"
}

resource "google_project_iam_member" "approved_apply_roles" {
  for_each = var.approved_project_roles
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.ci.email}"
}
