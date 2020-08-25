# Devolumizer

## What it does
The Devolumizer function iterates through a collection of AWS accounts and, for the specified regions, collects information about unattached EBS Volumes. It creates a report (CSV file) which is deposits into an s3 bucket for review. 

With remediation enabled, when a volume is first 'contacted' by Devolumizer, it is tagged with a ttl tag. The value is the date + 30 days. Once this ttl is expired, a snapshot of the volume is created, the volume is deleted and logged to a DynamoDB table. 

## Setup/Requirements
### Target roles
Each account to be reported on needs a role with read only rights and a trust policy to allow role assumption by this function's role. An example of this pattern can be seen [here](https://github.com/keepitsts/tf-Tydirium).

### IAM policy
This function must have the following policy permissions:
- Rights to create logs:
```

    {
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*",
      "Effect": "Allow"
    }
```
- Rights to assume the target role (above) in each account. The role name should be consistent because the code assumes the same role name in each account. 
```
    {
        "Effect": "Allow",
        "Action": "sts:AssumeRole",
        "Resource": [
          "arn:aws:iam::013229856305:role/${var.target_role}",
          "arn:aws:iam::896031873410:role/${var.target_role}",
          "arn:aws:iam::542153950015:role/${var.target_role}"
        ]
    }
```
- The function needs rights to access the DyDB table with account information. 
```
    {
        "Effect": "Allow",
        "Action": "dynamodb:Scan",
        "Resource": "arn:aws:dynamodb:${var.region}:${data.aws_caller_identity.current.account_id}:table/${var.table_name}"
    }
```
- The final two blocks allow the function to upload the report to the bucket:
```
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

```
### DyDB Account Table
The function queries a DyDB table for account information. The table name must be set as the `account_table` env var (below). This table is not currently created in the build process. The table data must include:
```
{'Id': '431537758516', 'Name': 'aws-sts-test'}
```
For each account to be scanned. These account numbers should correspond to the accounts listed in the second IAM block above.
Each item in the table should also have a `Devolumizer` attribute. Only accounts where this attribute is a boolean set to true will be evaluated. 

### DyDB Logging Table
The build terraform for this solution creates a table based on the `logging_table` value. The table has a primary key of volume_id (S). 

### S3 Report Bucket
The function writes its report to the bucket set at the `report_bucket` env var. This bucket is not currently created in the build process. 


## Env Vars

There are a few variables that are required to manage functionality

- `function_name` This is the name of the function. It is also the attribute on the Accounts DyDB table used to filter to ensure this function only runs in accounts where it is intended.

- `account_table` This is the name of the table where the account aliases and numbers are stored.

- `logging_table` This is the name of the DyDB table where deleted volumes are recorded for auditing. 

- `approved_regions` This is a string listing regions to be scanned. For example: `"us-east-1, us-east-2, us-west-1, us-west-2"`. Note that env vars must be strings not lists, so this string is converted in the code. 

- `report_bucket` Set to the name of bucket where report should be stored 

- `target_role` Set this to the name of the role that is assumed in the target accounts

- `remediation` Defaults to false. If set to "true", the reaper will delete volumes older than 30 days

## Notes/TODOs


- add threading to reduce time to execute
- update report to include unexpired volumes





# Devolumzier ProcessFlow
<img width="808" alt="Devolumzier-processFlow" src="https://user-images.githubusercontent.com/62033059/89531765-be055500-d7be-11ea-9f7b-ccd025154622.PNG">

# Devolumizer Architecture Diagram
<img width="524" alt="Devolumizer-arc-diagram" src="https://user-images.githubusercontent.com/62033059/89531713-ac23b200-d7be-11ea-896b-6ce903cbcf33.PNG">

# Local Enviroment Variables
<img width="784" alt="LEV" src="https://user-images.githubusercontent.com/62033059/89531778-c2317280-d7be-11ea-9e2c-50e137d06684.PNG">

# Test Scenarios
<img width="808" alt="Test-scenarios" src="https://user-images.githubusercontent.com/62033059/89531791-c65d9000-d7be-11ea-9e87-802ef34f13df.PNG">
