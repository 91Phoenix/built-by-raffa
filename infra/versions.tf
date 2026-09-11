terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # State is local by default. To share it, copy backend.tf.example to
  # backend.tf and create the bucket once; S3 state is a few cents a month.
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      project   = "bradicode"
      managed   = "terraform"
      component = "blog-api"
    }
  }
}
