"""
Lambda function that reports on unattached volumes and snapshots, deletes, and logs
unattached volumes that have been unattached for more than 30 days
Exempt volumes from lifecycling by creating a `ttl` tag and setting the value to any non valid date string.
"""
import time
from datetime import datetime, date, timedelta
import os
import csv
from pprint import pprint
import boto3

from tydirium import Tydirium

def get_accounts(client):
    """Get list of all accounts to check
    Args:
        client: dyDB boto3 client
    Returns: accounts: List; list of account aliases and ids
    """
    accounts = []
    account_table = os.environ['account_table']
    content = client.scan(TableName = account_table)
    # Opted not to create 2ndary key at this time- additional cost a factor,
    # and given assumed size of only 100~ items, performance should not be degraded. 
    for row in content["Items"]:
        if os.environ["function_name"] in row: 
            if row[os.environ["function_name"]]["BOOL"] == True:
                accounts.append({
                    "Name" : row["Name"]["S"],
                    "Id" : row["Id"]["S"]
                })
        
    return accounts

def write_csv(report_name, schema, data):
    """Writes csv with data
    Args:
        report_name: string; name of csv file
        schema: list; the columns of the csv
        data: list; list of rows to be written to the csv
        data = [
            [bucket1, 30],
            [bucket2, 60],
            [bucketthatdidntgetthememo, none]
        ]
    Returns:

    """
    with open('/tmp/{}.csv'.format(report_name), 'w') as csvfile:
        f = csv.writer(csvfile, quoting = csv.QUOTE_ALL)
        f.writerow(['Report generated at {}'.format(datetime.now())])
        f.writerow(schema)
        for row in data:
            f.writerow(row)

    
    return csvfile

def push_to_s3(file_name, bucket_name):
    """Puts arg into s3 bucket
    Args:
        file_name: string_name of csv in tmp directory
        bucket_name: string; bucket to store report in
    Returns:

    """
    s3 = boto3.client("s3")

    s3.upload_file("/tmp/{}.csv".format(file_name), bucket_name, "{}.csv".format(file_name))

def format_tags(tag_list):
    """Converts tags from list of key value pairs to a dict
    Args:
        tag_list: list; key value pairs ex.[{'Key': 'ttl', 'Value': '2020-07-17'}, {'Key': 'Poc', 'Value': 'Steve'}]
    Returns: tag_dict: dict; values expressed as: {'ttl': '2020-07-17', 'Poc': 'Steve'}
    """
    tag_dict = {}
    for tag in tag_list:
        tag_dict[tag["Key"]] = tag["Value"]

    return tag_dict

def create_ttl_tag(resource, volume_id, current_date):
    """creates tag on volume
    Args:
        resource: boto3 ec2 resource
        volume_id: string; volume id
        current_date: datetime object of current date
    Returns: None
    """
    volume_resource = resource.Volume(volume_id)
    volume_resource.create_tags(
        Tags=[
            {
                'Key': 'Ttl',
                'Value': str(current_date + timedelta(days=30))
            }
        ]
    )

def add_to_report(id, acct, region, size, volume_type, create_time, tags):
    """creates list of values to write to report
    Args:
        id: string; volume id
        acct: string; aws account alias
        region: string; region volume is in
        size: int; volume size in gb
        volume_type: string; volume type
        create_time: datetime; time volume was create
        tags: dict; key value pairs ex. {'ttl': '2020-07-17', 'Poc': 'Steve'}
    Returns: row: list; list of values to be written as line to csv
    """
    row = []
    row.append(id)
    row.append(acct)
    row.append(region)
    row.append(size)
    row.append(volume_type)
    row.append(create_time)
    if "Poc" in tags:
        row.append(tags["Poc"])
    else:
        row.append("No Contact Identified")
    if "Ttl" in tags:
        row.append(tags["Ttl"])
    else:
        row.append("")
    
    return row
                    
def delete_and_record(resource, client, volume_id, volume_type, size, region, tags):
    """deletes volume and records info in db
    Args:
        resource: boto3 ec2 resource for target account
        client: boto3 dydb client for reporting account
        volume_id: string; volume id
        volume_type: string; volume type
        size: int; volume size in gb
        region: string; region volume is in
        tags: dict; key value pairs ex. {'ttl': '2020-07-17',}
    Returns: None
    """
    volume_resource = resource.Volume(volume_id)
    # create snapshot
    if "Poc" in tags:
        Poc = tags["Poc"]
    else:
        Poc = "No Contact Identified"
    print("Snapshot initiated")
    snapshot = volume_resource.create_snapshot(
        Description="Automated Pre-remediation Snapshot {}".format(volume_id),
        TagSpecifications=[
            {
                "ResourceType": "snapshot", 
                "Tags": [
                    {
                        "Key": "VolumePoc",
                        "Value": Poc
                    }
                ]
            }
        ]
    )

    while snapshot.state == 'pending':
        print("Creating snapshot {}...".format(snapshot.snapshot_id))
        snapshot.load()
        print(snapshot.state)
        time.sleep(3)
    print("Snapshot complete")
    print("--------------------Deleting {}--------------------".format(volume_id))
    volume_resource.delete()

    logging_table=client.put_item(
        TableName=os.environ["logging_table"],
        Item={
            'volume_id' : {
                'S' : volume_id
            },
            'type' : {
                'S' : volume_type
            },
            'size' : {
                'N' : str(size)
            },
            'region' : {
                'S' : region
            },
            'terminate_timestamp' : {
                'S' : str(datetime.now())
            }
        }
    )

def lambda_handler(event, context):
    """Lambda function wrapping. 
    Args:
        event: cloudwatch event trigger data
        context: lambda methods and properties
    Returns: 
        
    """
    print('Starting function\n-------------------------------------------------')
    start_time = time.time()

    regions = os.environ['approved_regions'].split(", ")

    dydb_client = boto3.client('dynamodb')
    
    #create dict of alias : Tydirium inst
    accounts = get_accounts(dydb_client)

    clients = {}
    for account in accounts:
        for region in regions:
            clients["{}-{}".format(account["Name"], region)] = {}
            clients["{}-{}".format(account["Name"], region)]["region"] = region
            clients["{}-{}".format(account["Name"], region)]["account"] = account["Name"]
            clients["{}-{}".format(account["Name"], region)]["connection"] = Tydirium('ec2', account["Id"], os.environ['target_role'], region)
            print("created {} client & resource in {}".format(account["Name"], region))
    data = []
    current_date = date.today()
    for key, value in clients.items():
        # cycle through dict and describe volumes
        print("querying {}".format(key))
        # Handling for accounts where opt in required
        try:
            response = value["connection"].client.describe_volumes(
                Filters=[
                    {
                        'Name': 'status',
                        'Values': [
                            'available',
                        ]
                    },
                ],     
            )
            # print(response["Volumes"])
            for volume in response["Volumes"]:
                # print(volume)
                if "Tags" in volume:
                    tag_dict = format_tags(volume["Tags"])
                else:
                    tag_dict = {}

                # CASE No Tags
                if "Tags" not in volume:
                    print("No Tags on {}".format(volume["VolumeId"]))
                    if os.environ["remediation"] == 'true':
                        create_ttl_tag(value["connection"].resource, volume["VolumeId"], current_date)
                    data.append(
                        add_to_report(
                            volume["VolumeId"],
                            value['account'],
                            value['region'],
                            volume["Size"],
                            volume["VolumeType"],
                            volume["CreateTime"],
                            tag_dict
                        )
                    )

                # CASE No Ttl
                elif "Ttl" not in tag_dict: 
                    print("No Ttl on {}".format(volume["VolumeId"]))
                    if os.environ["remediation"] == 'true':
                        create_ttl_tag(value["connection"].resource, volume["VolumeId"], current_date)
                    data.append(
                        add_to_report(
                            volume["VolumeId"],
                            value['account'],
                            value['region'],
                            volume["Size"],
                            volume["VolumeType"],
                            volume["CreateTime"],
                            tag_dict
                        )
                    )

                
                else:
                    try:
                        datetime.strptime(tag_dict["Ttl"], '%Y-%m-%d')
                        # CASE Unexpired Ttl
                        if ("Ttl" in tag_dict) and (datetime.strptime(tag_dict["Ttl"], '%Y-%m-%d').date() >= current_date):
                            print("Ttl not expired for {}".format(volume["VolumeId"]))
                            # disabled b/c current requirement is not reporting on compliant volumes. Uncomment to re-enable. 
                            # data.append(
                            #     add_to_report(
                            #         volume["VolumeId"],
                            #         value['account'],
                            #         value['region'],
                            #         volume["Size"],
                            #         volume["VolumeType"],
                            #         volume["CreateTime"],
                            #         tag_dict
                            #     )
                            # )

                        # CASE Expired Ttl
                        if ("Ttl" in tag_dict) and (datetime.strptime(tag_dict["Ttl"], '%Y-%m-%d').date() < current_date):
                            if os.environ["remediation"] == 'true':
                                print("Ttl expired for {}".format(volume["VolumeId"]))
                                delete_and_record(
                                    value["connection"].resource, 
                                    dydb_client, 
                                    volume["VolumeId"],
                                    volume["VolumeType"],
                                    volume["Size"],
                                    value['region'],
                                    tag_dict
                                    )
                            else:
                                data.append(
                                    add_to_report(
                                        volume["VolumeId"],
                                        value['account'],
                                        value['region'],
                                        volume["Size"],
                                        volume["VolumeType"],
                                        volume["CreateTime"],
                                        tag_dict
                                    )
                                )
                        
                    except Exception as e:
                        # CASE Other Ttl
                        print("Ttl not valid date on {}".format(volume["VolumeId"]))
                        print(e)
                        data.append(
                            add_to_report(
                                volume["VolumeId"],
                                value['account'],
                                value['region'],
                                volume["Size"],
                                volume["VolumeType"],
                                volume["CreateTime"],
                                tag_dict
                            )
                        )

        except Exception as e:
            print("Error occurred in {}:".format(key))
            print(e)
            pass

    # write volumes to report
    print("Writing report file")
    report_name = "orphaned_volumes"
    schema = ["Volume ID", "Account", "Region", "Size", "Type", "Creation Time", "Point of Contact", "Termination Date"]
    report = write_csv(report_name, schema, data)

    # upload report to bucket 
    print("uploading to s3")

    bucket = os.environ["report_bucket"]

    upload = push_to_s3(report_name, bucket)





    end_time = time.time() - start_time
    print('Time required: {0:.2f} s'.format(end_time))

