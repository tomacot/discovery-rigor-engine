"""
Discovery Rigor Engine — CDK main stack.

Deploys all AWS resources with a single `cdk deploy`.

Resources:
  - ECR: Docker image (built locally, pushed to ECR during deploy)
  - VPC: Public subnets only — no NAT gateway, keeps costs near zero
  - ECS Fargate: Streamlit container, runs in public subnet
  - Application Load Balancer: public HTTP endpoint with native WebSocket support
  - IAM task role: lets the running container call Bedrock, DynamoDB, S3
  - IAM execution role: lets ECS pull the image from ECR (auto-created by CDK)
  - DynamoDB: persistent study state (ready for future DynamoDB store integration)
  - S3: fixture data (ready for future S3 fixture integration)

Why ECS Fargate + ALB over App Runner:
  App Runner does not reliably support WebSocket upgrade requests. Streamlit
  requires WebSockets for all real-time browser <-> server communication.
  ALB natively supports HTTP Upgrade (WebSocket) — it passes the Upgrade
  header through to the container unchanged. ECS Fargate runs the same
  Docker image with the same environment variables.

  Trade-off: Fargate doesn't scale to zero (App Runner does). For a low-traffic
  deployment, the always-on cost is ~$0.012/hour (~$9/month).

Two IAM roles:
  task_role (AppInstanceRole): what the container can call at runtime —
    Bedrock, DynamoDB, S3.
  execution_role: what ECS can do to start the task — pull image from ECR,
    write logs to CloudWatch. CDK creates this automatically.
"""

from __future__ import annotations

import aws_cdk as cdk
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecr_assets as ecr_assets
import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_ecs_patterns as ecs_patterns
import aws_cdk.aws_iam as iam
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_deployment as s3_deployment
from constructs import Construct

BEDROCK_MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"


class DiscoveryRigorStack(cdk.Stack):
    """Single-stack deployment of the Discovery Rigor Engine on AWS."""

    def __init__(self, scope: Construct, stack_id: str, **kwargs) -> None:
        super().__init__(scope, stack_id, **kwargs)

        # ── Docker image ──────────────────────────────────────────────────────
        # CDK builds the image from the Dockerfile at project root and pushes
        # it to an ECR repository it manages. The image_tag is a content hash,
        # so the image is only rebuilt when files change.
        docker_image = ecr_assets.DockerImageAsset(
            self,
            "AppImage",
            directory="..",  # Project root — where Dockerfile lives
        )

        # ── IAM: task role (container → AWS services) ─────────────────────────
        # Assumed by the running container. Governs what application code can
        # call — Bedrock, DynamoDB, S3. ECS task principal, not App Runner.
        task_role = iam.Role(
            self,
            "AppInstanceRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description="Runtime permissions for the app container: Bedrock, DynamoDB, S3",
        )

        # Bedrock: allow calling Claude Sonnet 4 via cross-region inference profile.
        # Claude 4 models require the us. inference profile prefix — direct on-demand
        # invocation of the base model ID is not supported.
        task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/anthropic.claude-sonnet-4-20250514-v1:0",
                    f"arn:aws:bedrock:*:{self.account}:inference-profile/{BEDROCK_MODEL_ID}",
                ],
            )
        )

        # ── DynamoDB: study state ─────────────────────────────────────────────
        studies_table = dynamodb.Table(
            self,
            "StudiesTable",
            table_name="discovery-rigor-studies",
            partition_key=dynamodb.Attribute(
                name="study_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY,  # Fine for a demo
        )
        studies_table.grant_read_write_data(task_role)

        # ── S3: fixture data ──────────────────────────────────────────────────
        fixture_bucket = s3.Bucket(
            self,
            "FixtureBucket",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )
        s3_deployment.BucketDeployment(
            self,
            "FixtureDeployment",
            sources=[s3_deployment.Source.asset("../data")],
            destination_bucket=fixture_bucket,
            destination_key_prefix="fixtures/",
        )
        fixture_bucket.grant_read(task_role)

        # ── VPC ───────────────────────────────────────────────────────────────
        # Public subnets only — no NAT gateway. Fargate tasks run in public
        # subnets with public IPs, so they can reach ECR and Bedrock directly.
        # Saves ~$32/month per NAT gateway for a demo that doesn't need private
        # subnet isolation.
        vpc = ec2.Vpc(
            self,
            "AppVpc",
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
            ],
        )

        # ── ECS Cluster ───────────────────────────────────────────────────────
        cluster = ecs.Cluster(self, "AppCluster", vpc=vpc)

        # ── Fargate service + ALB ─────────────────────────────────────────────
        # ApplicationLoadBalancedFargateService is a CDK pattern that creates
        # and wires together: ALB, target group, listener, Fargate task definition,
        # ECS service, security groups, and log group. One construct vs ~15 separate.
        #
        # assign_public_ip=True: required because the task runs in a public subnet
        # with no NAT gateway. Without a public IP the task can't reach ECR.
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "StreamlitService",
            cluster=cluster,
            cpu=512,           # 0.5 vCPU — sufficient for Streamlit + LangGraph
            memory_limit_mib=1024,  # 1 GB — LLM response parsing uses some memory
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_ecr_repository(
                    docker_image.repository,
                    tag=docker_image.image_tag,
                ),
                container_port=8501,
                environment={
                    "AWS_REGION": self.region,
                    "BEDROCK_MODEL_ID": BEDROCK_MODEL_ID,
                    "DYNAMODB_TABLE": studies_table.table_name,
                    "S3_BUCKET": fixture_bucket.bucket_name,
                },
                task_role=task_role,
                log_driver=ecs.LogDrivers.aws_logs(
                    stream_prefix="discovery-rigor",
                ),
            ),
            public_load_balancer=True,
            assign_public_ip=True,
        )

        # Grant the auto-created ECS execution role permission to pull the image.
        # The execution role is separate from the task role — it's used by ECS
        # to pull the image from ECR and write logs, not by the container itself.
        docker_image.repository.grant_pull(
            fargate_service.task_definition.execution_role  # type: ignore[arg-type]
        )

        # Streamlit health check — /_stcore/health returns 200 "ok" when the
        # server is ready. Using this instead of "/" because "/" returns full HTML
        # which is heavier to parse and slower to respond during startup.
        fargate_service.target_group.configure_health_check(
            path="/_stcore/health",
            healthy_http_codes="200",
            interval=cdk.Duration.seconds(30),
            timeout=cdk.Duration.seconds(10),
            healthy_threshold_count=2,
            unhealthy_threshold_count=5,
        )

        # ── Outputs ───────────────────────────────────────────────────────────
        cdk.CfnOutput(
            self,
            "ServiceUrl",
            value=f"http://{fargate_service.load_balancer.load_balancer_dns_name}",
            description="Public URL for the deployed application",
        )
        cdk.CfnOutput(
            self,
            "DynamoDbTable",
            value=studies_table.table_name,
            description="DynamoDB table name",
        )
        cdk.CfnOutput(
            self,
            "FixtureBucketName",
            value=fixture_bucket.bucket_name,
            description="S3 bucket for fixture data",
        )
