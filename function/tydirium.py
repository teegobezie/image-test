import boto3

class Tydirium():
    session = boto3.session.Session()

    sts_client = session.client('sts')

    def __init__(self, service, account, role, region):
        self.service = service
        self.account = account
        self.role = role
        self.region = region
        self.connection = self.sts_client.assume_role(
            RoleArn = "arn:aws:iam::{}:role/{}".format(self.account, self.role),
            RoleSessionName = "{}_{}_session".format(self.account, self.role),
            DurationSeconds=900 #15 min is the shortest ttl
        )
        self.AccessKeyId = self.connection['Credentials']['AccessKeyId']
        self.SecretAccessKey = self.connection['Credentials']['SecretAccessKey']
        self.SessionToken = self.connection['Credentials']['SessionToken']
        self.client =  boto3.client(
            self.service,
            aws_access_key_id = self.AccessKeyId,
            aws_secret_access_key = self.SecretAccessKey,
            aws_session_token = self.SessionToken,
            region_name = self.region
            )
        self.resource =  boto3.resource(
            self.service,
            aws_access_key_id = self.AccessKeyId,
            aws_secret_access_key = self.SecretAccessKey,
            aws_session_token = self.SessionToken,
            region_name = self.region
            )

