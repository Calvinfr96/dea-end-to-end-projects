from aws_cdk import (
    Stack,
    SecretValue,
    aws_s3 as s3,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as actions,
    aws_codebuild as codebuild
)
from constructs import Construct

class WistiaPipelineStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Artifact bucket for staging templates and interim scripts
        artifact_bucket = s3.Bucket(self, "PipelineArtifactBucket")

        # Define tracking variables
        source_output = codepipeline.Artifact()
        build_output = codepipeline.Artifact()

        # 1. PIPELINE SOURCE ACTION (GitHub Integration)
        # Uses GitHub CodeStar Connection Action instead of a GitHub Personal Access Token (PAT) stored inside Secrets Manager.
        source_action = actions.CodeStarConnectionsSourceAction(
            action_name="GitHub_Source",
            owner="Calvinfr96",
            repo="dea-wistia-analytics-code-pipeline",
            branch="main",
            output=source_output,
            # Paste the ARN you copied from Step 1 here
            connection_arn="arn:aws:codeconnections:us-east-1:515424600331:connection/22cfdb4a-8ab5-4f20-808e-4df7fa8e7fa9"
        )

        # 2. PIPELINE BUILD ACTION (AWS CodeBuild)
        pipeline_project = codebuild.PipelineProject(
            self, "WistiaBuildProject",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0
            ),
            # Instruct CodeBuild to handle script synching and CDK synthesis
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "install": {
                        "commands": ["npm install -g aws-cdk", "pip install -r requirements.txt"]
                    },
                    "build": {
                        "commands": [
                            "cdk synth",
                            # Sync the PySpark scripts folder up directly into S3 for Glue to reference
                            "aws s3 cp src/transformation/ s3://YOUR-RAW-BUCKET-NAME/scripts/ --recursive"
                        ]
                    }
                },
                "artifacts": {
                    "base-directory": "cdk.out",
                    "files": ["*.template.json"]
                }
            })
        )

        build_action = actions.CodeBuildAction(
            action_name="CDK_Build",
            project=pipeline_project,
            input=source_output,
            outputs=[build_output]
        )

        # 3. CONSTRUCT PIPELINE ORCHESTRATION
        pipeline = codepipeline.Pipeline(
            self, "WistiaDeploymentPipeline",
            artifact_bucket=artifact_bucket,
            stages=[
                codepipeline.StageProps(stage_name="Source", actions=[source_action]),
                codepipeline.StageProps(stage_name="Build", actions=[build_action]),
                # Add a deployment stage pointing to CloudFormation CreateUpdateStackAction below
            ]
        )
