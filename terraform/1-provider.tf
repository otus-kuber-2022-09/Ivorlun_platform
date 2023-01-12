# https://registry.terraform.io/providers/hashicorp/google/latest/docs
provider "google" {
  project = "kuber-play-372114"
  region  = "europe-west4"
}

# https://www.terraform.io/language/settings/backends/gcs
terraform {
  backend "gcs" {
    bucket = "terraform-kuber-play"
    prefix = "terraform/state"
  }
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.48"
    }
  }
}
