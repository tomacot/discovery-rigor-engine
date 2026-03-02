"""
CDK entry point — instantiates the stack and binds it to the AWS environment.

Usage:
  cd infrastructure/
  cdk deploy              # Deploy all resources
  cdk diff                # Preview changes
  cdk destroy             # Tear down all resources

Prerequisites:
  1. AWS account with Bedrock Claude 3.5 Sonnet access approved
  2. AWS CLI configured: aws configure (or use IAM Identity Center)
  3. CDK bootstrapped: cdk bootstrap aws://ACCOUNT_ID/REGION
  4. Install CDK: npm install -g aws-cdk
  5. Install infra dependencies: pip install aws-cdk-lib aws-cdk.aws-apprunner-alpha constructs
"""

import aws_cdk as cdk

from stacks.main_stack import DiscoveryRigorStack

app = cdk.App()

DiscoveryRigorStack(
    app,
    "DiscoveryRigorEngine",
    description="Discovery Rigor Engine — PM research tool on AWS App Runner + Bedrock",
    env=cdk.Environment(
        # Uses the account and region from AWS CLI profile / environment variables.
        # To target a specific account: account="123456789012", region="us-east-1"
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1",
    ),
)

app.synth()
