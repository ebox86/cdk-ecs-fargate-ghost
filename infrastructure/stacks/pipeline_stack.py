from aws_cdk import (
    aws_s3 as s3,
    aws_ecr,
    aws_codebuild,
    aws_ssm,
    aws_codepipeline,
    aws_codepipeline_actions,
    core
    )

class Pipeline_stack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # pipeline requires versioned bucket
        bucket = s3.Bucket(
            self, "SourceBucket",
            bucket_name=f"{props['namespace'].lower()}-{core.Aws.ACCOUNT_ID}",
            versioned=True,
            removal_policy=core.RemovalPolicy.DESTROY)

        # ecr repo to push docker container into
        ecr = aws_ecr.Repository(
            self, "ECR",
            repository_name=props['namespace'],
            removal_policy=core.RemovalPolicy.DESTROY
        )

        # codebuild project meant to run in pipeline
        cb_docker_build = aws_codebuild.PipelineProject(
            self, "DockerBuild",
            project_name=f"{props['namespace']}-Docker-Build",
            build_spec=aws_codebuild.BuildSpec.from_source_filename(
                filename='./docker/buildspec.yml'),
            environment=aws_codebuild.BuildEnvironment(
                privileged=True,
            ),
            environment_variables={
                'IMAGE_REPO_NAME': aws_codebuild.BuildEnvironmentVariable(
                    value=ecr.repository_name),
                'IMAGE_TAG': aws_codebuild.BuildEnvironmentVariable(
                    value='latest'),
                'AWS_ACCOUNT_ID': aws_codebuild.BuildEnvironmentVariable(
                    value=core.Aws.ACCOUNT_ID),
                'AWS_DEFAULT_REGION': aws_codebuild.BuildEnvironmentVariable(
                    value=core.Aws.REGION)
            },
            description='Pipeline for CodeBuild',
            timeout=core.Duration.minutes(60),
        )
        # codebuild iam permissions to read write s3
        bucket.grant_read_write(cb_docker_build)

        # codebuild permissions to interact with ecr
        ecr.grant_pull_push(cb_docker_build)

        # define the s3 artifact
        source_output = aws_codepipeline.Artifact(artifact_name='source')

        # define the pipeline
        pipeline = aws_codepipeline.Pipeline(
            self, "Pipeline",
            pipeline_name=f"{props['namespace']}-pipeline",
            artifact_bucket=bucket,
            restart_execution_on_update=True,
            stages=[
                aws_codepipeline.StageProps(
                    stage_name='Source',
                    actions=[
                        aws_codepipeline_actions.GitHubSourceAction(
                            action_name='Checkout',
                            owner=props['github-owner'],
                            repo=props['github-repository'],
                            oauth_token=core.SecretValue.secrets_manager('GitHubToken'),
                            output=source_output,
                            trigger=aws_codepipeline_actions.GitHubTrigger.WEBHOOK,
                        ),
                    ]
                ),
                aws_codepipeline.StageProps(
                    stage_name='Build',
                    actions=[
                        aws_codepipeline_actions.CodeBuildAction(
                            action_name='DockerBuildImage',
                            input=source_output,
                            project=cb_docker_build,
                            run_order=1,
                        )
                    ]
                )
            ]
        )
        # give pipeline role read write to the bucket
        bucket.grant_read_write(pipeline.role)


        self.output_props = props.copy()
        self.output_props['ecr'] = ecr

        # cfn output
        core.CfnOutput(
            self, "PipelineOut",
            description="Pipeline",
            value=pipeline.pipeline_name
        )

        core.CfnOutput(
            self, "ECRURI",
            description="ECR URI",
            value=ecr.repository_uri,
        )
        core.CfnOutput(
            self, "S3Bucket",
            description="S3 Bucket",
            value=bucket.bucket_name
        )

    @property
    def outputs(self):
        return self.output_props
