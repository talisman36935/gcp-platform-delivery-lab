mock_provider "google" {}

variables {
  project_id          = "synthetic-portfolio-test"
  operator_cidr       = "192.0.2.10/32"
  config_sync_version = "1.0.0"
  source_revision     = "0000000000000000000000000000000000000000"
}

run "regional_three_node_contract" {
  command = plan
  assert {
    condition     = google_container_cluster.lab.location == "europe-west2" && length(google_container_cluster.lab.node_locations) == 3
    error_message = "Regional control plane and three worker zones required."
  }
  assert {
    condition     = google_container_node_pool.lab.node_count == 1 && length(google_container_node_pool.lab.node_locations) == 3 && google_container_node_pool.lab.node_config[0].machine_type == "e2-standard-2"
    error_message = "Use three total e2-standard-2 nodes, not nine."
  }
}

run "foreign_region_rejected" {
  command = plan
  variables { region = "us-central1" }
  expect_failures = [var.region]
}

run "single_zone_rejected" {
  command = plan
  variables { zones = ["europe-west2-a"] }
  expect_failures = [var.zones]
}
