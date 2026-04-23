"""
setup_logging.py — Enable Bedrock model invocation logging for a given AWS profile.

Creates:
  1. CloudWatch log group (if it doesn't exist)
  2. IAM role with trust policy for bedrock.amazonaws.com
  3. IAM policy granting CloudWatch write access
  4. Bedrock model invocation logging configuration pointing at the log group

Usage:
    python setup_logging.py [--profile PROFILE] [--region REGION] [--log-group LOG_GROUP]

Defaults are read from config.yaml if not provided.
"""
import argparse
import json
import sys
import time

import boto3
import yaml
from botocore.exceptions import ClientError

ROLE_NAME = "BedrockInvocationLoggingRole"
POLICY_NAME = "BedrockInvocationLoggingPolicy"


def load_config(path="config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def get_account_id(session):
    return session.client("sts").get_caller_identity()["Account"]


def ensure_log_group(logs_client, log_group):
    try:
        logs_client.create_log_group(logGroupName=log_group)
        print(f"Created log group: {log_group}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
            print(f"Log group already exists: {log_group}")
        else:
            raise


def ensure_iam_role(iam_client, account_id, log_group, region):
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "bedrock.amazonaws.com"},
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {"aws:SourceAccount": account_id},
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock:{region}:{account_id}:*"
                    },
                },
            }
        ],
    }

    # Create or fetch the role
    try:
        role = iam_client.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Allows Bedrock to write model invocation logs to CloudWatch",
        )["Role"]
        print(f"Created IAM role: {ROLE_NAME}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            role = iam_client.get_role(RoleName=ROLE_NAME)["Role"]
            # Update trust policy in case it's stale
            iam_client.update_assume_role_policy(
                RoleName=ROLE_NAME,
                PolicyDocument=json.dumps(trust_policy),
            )
            print(f"IAM role already exists, trust policy updated: {ROLE_NAME}")
        else:
            raise

    role_arn = role["Arn"]

    # Inline policy granting CloudWatch write access to the specific log group
    log_group_arn = f"arn:aws:logs:{region}:{account_id}:log-group:{log_group}:*"
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                "Resource": log_group_arn,
            }
        ],
    }

    iam_client.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName=POLICY_NAME,
        PolicyDocument=json.dumps(policy_document),
    )
    print(f"Attached inline policy {POLICY_NAME} to {ROLE_NAME}")

    return role_arn


def enable_bedrock_logging(bedrock_client, log_group, role_arn):
    logging_config = {
        "cloudWatchConfig": {
            "logGroupName": log_group,
            "roleArn": role_arn,
        },
        "textDataDeliveryEnabled": True,
        "imageDataDeliveryEnabled": False,
        "embeddingDataDeliveryEnabled": False,
    }

    bedrock_client.put_model_invocation_logging_configuration(
        loggingConfig=logging_config
    )
    print("Bedrock model invocation logging enabled.")


def verify(bedrock_client, log_group):
    cfg = bedrock_client.get_model_invocation_logging_configuration().get("loggingConfig", {})
    actual = cfg.get("cloudWatchConfig", {}).get("logGroupName")
    if actual == log_group:
        print(f"Verified: Bedrock is logging to {log_group}")
    else:
        print(f"Warning: expected log group {log_group!r}, got {actual!r}")


def main():
    config = load_config()

    parser = argparse.ArgumentParser(description="Enable Bedrock invocation logging")
    parser.add_argument("--profile", default=config["aws"]["profile"])
    parser.add_argument("--region", default=config["aws"]["region"])
    parser.add_argument("--log-group", default=config["aws"]["log_group_name"])
    args = parser.parse_args()

    print(f"Profile:   {args.profile}")
    print(f"Region:    {args.region}")
    print(f"Log group: {args.log_group}")
    print()

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    account_id = get_account_id(session)
    print(f"Account:   {account_id}")
    print()

    logs_client = session.client("logs")
    iam_client = session.client("iam")
    bedrock_client = session.client("bedrock")

    ensure_log_group(logs_client, args.log_group)
    role_arn = ensure_iam_role(iam_client, account_id, args.log_group, args.region)

    # IAM role propagation can take a few seconds
    print("Waiting for IAM role to propagate...")
    time.sleep(10)

    enable_bedrock_logging(bedrock_client, args.log_group, role_arn)
    verify(bedrock_client, args.log_group)

    print()
    print("Done. Bedrock will now log invocations to CloudWatch.")
    print(f"Run the cost monitor with: python main.py")


if __name__ == "__main__":
    main()
