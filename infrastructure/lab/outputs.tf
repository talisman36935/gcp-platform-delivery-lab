output "cluster_name" {
  value = google_container_cluster.lab.name
}
output "membership" {
  value = google_gke_hub_membership.lab.id
}
