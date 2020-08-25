variable "bucket_name" {}
variable "function_name" {}
variable "commit_id" {}

provider "aws" {
  region = "us-east-1"
  assume_role {
      role_arn = "arn:aws:iam::737855703655:role/JenkinsAssumedRole"
  }
}
terraform {
    backend "s3" {
        bucket = "sts-cp-remote-state"
        key = "Devolumeizer"
        region = "us-east-1"
        role_arn = "arn:aws:iam::737855703655:role/JenkinsAssumedRole"
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
  report_bucket  = ""
  target_role = "lambdaAssumedRole"
  master_account = "928780296683"
 }

