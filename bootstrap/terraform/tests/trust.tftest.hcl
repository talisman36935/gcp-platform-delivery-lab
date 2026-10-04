mock_provider "google" {}

variables {
  project_id        = "synthetic-portfolio-test"
  region            = "europe-west2"
  state_bucket_name = "synthetic-portfolio-state"
}

run "bootstrap_has_no_default_cloud_apply_roles" {
  command = plan
  assert {
    condition     = length(google_project_iam_member.approved_apply_roles) == 0
    error_message = "Bootstrap must not silently grant project apply privileges."
  }
  assert {
    condition     = google_storage_bucket.state.public_access_prevention == "enforced" && google_storage_bucket.state.uniform_bucket_level_access
    error_message = "State must remain private under uniform access."
  }
}

run "broad_editor_role_is_rejected" {
  command = plan
  variables { approved_project_roles = ["roles/editor"] }
  expect_failures = [var.approved_project_roles]
}
