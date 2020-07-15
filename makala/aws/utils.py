"""AWS utilities to support makala
"""

import sys
import logging
import boto3
import os

def main():
    print(get_caller_account())
    role_name = "foo-bar-{}".format(os.getpid())
    create_lambda_role(role_name=role_name, vpc=True)
    print(role_name)

def lambda_add_permission(function_name, action, **kwargs):
    lambda_client = boto3.client('lambda')

    account = kwargs.get("account") or get_caller_account()
    args = {"FunctionName": function_name, "Action": action, "SourceAccount" : account}
    if kwargs.get("source_arn"):
        args["SourceArn"] = kwargs["source_arn"]

    lambda_client.add_permission(**args)

def get_caller_identity():
    sts = boto3.client('sts')
    response = sts.get_caller_identity()
    return response

def get_caller_account():
    identity = get_caller_identity()
    return identity["Account"]

def list_role_policies(role_name):
    iam = boto3.client('iam')
    response = iam.list_attached_role_policies(RoleName=role_name)
    return [ p["PolicyArn"] for p in response["AttachedPolicies"]]

def detach_role_policy(role_name, policy_arn):
    iam = boto3.client('iam')
    iam.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)

def delete_role(role_name):
    iam = boto3.client('iam')
    iam.delete_role(RoleName=role_name)

def validate_role(role_name):
    """validates a role
    """
    iam = boto3.client('iam')
    try:
        role = iam.get_role(RoleName=role_name)
        if "Role" in role and "Arn" in role["Role"]:
            arn = role["Role"]["Arn"]
    except iam.exceptions.NoSuchEntityException:
        arn = None

    return arn


def create_lambda_role(**kwargs):
    """Create a basic Lambda execution role and attach policies
    """
    role_name = kwargs["role_name"]
    vpc = kwargs["vpc"]
    role_arn = validate_role(role_name)
    if not role_arn:
        role_arn = create_lambda_execution_role(role_name, vpc=vpc)

    return role_arn

def get_subnet_ids(vpc_id):
    """Get the subnet ids for the given VPC
    """
    ec2 = boto3.client('ec2')
    subnets = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
    subnet_ids = None
    if subnets:
        subnet_ids = [s["SubnetId"] for s in subnets["Subnets"]]  # pylint: disable=C0103

    return subnet_ids


def get_default_security_group(vpc_id):
    """Get the default security group for the given VPC
    """

    ec2 = boto3.client('ec2')
    default_sg = None

    security_groups = ec2.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])

    if security_groups:
        default_sg = [sg for sg in security_groups["SecurityGroups"]
                      if sg["GroupName"] == "default"][0]

    return default_sg


def get_default_vpc():
    """Get the default VPC configuration.
    """
    ec2 = boto3.client('ec2')
    vpcs = ec2.describe_vpcs()
    default_vpc = {}
    if vpcs:
        default_vpc = [v for v in vpcs["Vpcs"] if v["IsDefault"]][0]

    return default_vpc


def create_lambda_execution_role(role_name, **kwargs):
    """Create a basic execution role for the Lambda
    """
    role_arn = None
    iam = boto3.client('iam')

    policy_arns = []
    if kwargs["vpc"]:
        policy_arns.append("arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole")
    else:
        policy_arns.append("arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")

    try:
        policy = '{"Version": "2012-10-17",' \
                 '"Statement": [{ "Effect": "Allow", ' \
                 '"Principal": {"Service": "lambda.amazonaws.com"}, ' \
                 '"Action": "sts:AssumeRole"}]}'
        logger = logging.getLogger()
        logger.info("creating basicexecution role: {}".format(role_name))
        role = iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=policy)
        role_arn = role["Role"]["Arn"]

        for arn in policy_arns:
            iam.attach_role_policy(RoleName=role_name, PolicyArn=arn)
            logger.info("attaching policy: {} to role: {}".format(arn, role_name))
    except iam.exceptions.EntityAlreadyExistsException:
        logger.warn("role {} already exists".format(role_name))

    return role_arn

def get_private_subnet_ids(vpc_id):
    ec2 = boto3.client('ec2')
    response = ec2.describe_route_tables(Filters = [{ "Name": "vpc-id", "Values": [ vpc_id ] }])
    route_tables = response["RouteTables"]

    private_subnets = []

    for rt in route_tables:
        routes = rt["Routes"]
        for r in routes:
            if r["DestinationCidrBlock"] == "0.0.0.0/0" and r.get("NatGatewayId"):
                private_subnets = [s["SubnetId"] for s in rt["Associations"]]

    return private_subnets

if __name__ == "__main__":
    main()
