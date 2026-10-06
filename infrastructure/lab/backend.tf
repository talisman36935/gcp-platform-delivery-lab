terraform {
  backend "local" {
    path = ".terraform/ephemeral-lab.tfstate"
  }
}
