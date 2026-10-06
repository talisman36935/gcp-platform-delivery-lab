terraform {
  backend "local" {
    path = ".terraform/ephemeral-bootstrap.tfstate"
  }
}
