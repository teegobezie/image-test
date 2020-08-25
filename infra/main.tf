
# Variables
variable "bucket_name" {}
variable "function_name" {}
variable "commit_id" {}
variable "region" {
  default = "us-east-1"
}
variable "handler" {
  default = "lambda_function.lambda_handler"
}
variable "runtime" {
  default = "python3.7"
}
variable "logging_table" {}
# Env Vars
variable "account_table" {}
variable "approved_regions" {
  default = "us-east-1, us-east-2, us-west-1, us-west-2"
}
variable "report_bucket" {}
variable "target_role" {}
variable "remediation" {
  default = "false"
}




# Data
data "aws_caller_identity" "current" {}

# Resources
resource "aws_lambda_function" "function" {
  function_name = var.function_name

  s3_bucket = var.bucket_name
  s3_key    = "${var.function_name}/${var.commit_id}.zip"

  publish = false
  memory_size = 192 # 256
  timeout = 300
  reserved_concurrent_executions = -1


  handler = var.handler
  runtime = var.runtime

  role = aws_iam_role.lambda_exec.arn



  environment {
    variables = {
      function_name = var.function_name
      account_table = var.account_table
      logging_table = var.logging_table
      approved_regions = var.approved_regions
      report_bucket = var.report_bucket
      target_role = var.target_role
      remediation = var.remediation
    }
  }

  tags = {
    Poc = "wesley.coffay@keepitsts.com"
  }
}
resource "aws_iam_role" "lambda_exec" {
  name = "${var.function_name}_role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}
resource "aws_dynamodb_table" "logging_table" {
  name = var.logging_table
  billing_mode = "PROVISIONED"
  read_capacity = 5
  write_capacity = 5
  hash_key = "volume_id"
  attribute {
      name = "volume_id"
      type = "S"
  }
  tags = {
    Poc = "wesley.coffay@keepitsts.com"
    CostCode = "Innohub"
  }
}
# See also the following AWS managed policy: AWSLambdaBasicExecutionRole
resource "aws_iam_policy" "lambda_logging" {
  name = "${var.function_name}_policy"
  path = "/"
  description = "IAM policy for logging from a lambda"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*",
      "Effect": "Allow"
    },
    {
        "Effect": "Allow",
        "Action": "sts:AssumeRole",
        "Resource": [
          "arn:aws:iam::803178833131:role/${var.target_role}",
          "arn:aws:iam::552752748819:role/${var.target_role}",
          "arn:aws:iam::928780296683:role/${var.target_role}",
          "arn:aws:iam::702067219081:role/${var.target_role}",
          "arn:aws:iam::216860627738:role/${var.target_role}",
          "arn:aws:iam::613990751446:role/${var.target_role}",
          "arn:aws:iam::559949369362:role/${var.target_role}",
          "arn:aws:iam::667808422948:role/${var.target_role}",
          "arn:aws:iam::737855703655:role/${var.target_role}",
          "arn:aws:iam::345248387622:role/${var.target_role}",
          "arn:aws:iam::636935307102:role/${var.target_role}"
        ]
    },
    {
        "Effect": "Allow",
        "Action": "dynamodb:Scan",
        "Resource": "arn:aws:dynamodb:${var.region}:${data.aws_caller_identity.current.account_id}:table/${var.account_table}"
    },
    {
        "Effect": "Allow",
        "Action": "dynamodb:PutItem",
        "Resource": "arn:aws:dynamodb:${var.region}:${data.aws_caller_identity.current.account_id}:table/${var.logging_table}"
    },
    {
        "Effect": "Allow",
        "Action": [
            "s3:ListBucket"
        ],
        "Resource": [
            "arn:aws:s3:::${var.report_bucket}"
        ]
    },
    {
        "Effect": "Allow",
        "Action": "s3:PutObject",
        "Resource": [
          "arn:aws:s3:::${var.report_bucket}/*"
        ]
    }    
  ]
}
EOF
}
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role = "${aws_iam_role.lambda_exec.name}"
  policy_arn = "${aws_iam_policy.lambda_logging.arn}"
}
