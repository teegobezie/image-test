variable "bucket_name" {}
variable "function_name" {}
variable "commit_id" {}

provider "aws" {
  region = "us-east-1"
  assume_role {
    role_arn     = "arn:aws:iam::345248387622:role/JenkinsAssumedRole"
  }
}
terraform {
    backend "s3" {
        bucket = "sts-np-compliance-tf"
        key = "Devolumeizer"
        region = "us-east-1"
        role_arn     = "arn:aws:iam::345248387622:role/JenkinsAssumedRole"
    }
  required_version = "0.12.10"
}
module "function" {
  source = "../infra"
  
  bucket_name = var.bucket_name
  function_name = var.function_name
  commit_id = var.commit_id

  account_table = "CorpAccts"
  logging_table = "DeletedVolumes"
  report_bucket = "sts-np-reporting"
  target_role = "lambdaAssumedRole"
  remediation = "false"
}
