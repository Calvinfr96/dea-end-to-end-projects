# CRM Lead Assignment Project Summary

## GitHub Actions Workflow (AWS CodePipeline Alternative)
- Create a GitHub repository that will be linked with AWS. The repository should store the required Python scripts and configuration files in the following manner:
    ```
    ├── bin/
    │   └── lead-pipeline.ts
    ├── lib/
    │   └── lead-pipeline-stack.ts  <-- Put the CDK code here
    ├── lambda/                     <-- Create this folder
    │   └── index.js                <-- Your runtime Lambda code
    ├── cdk.json
    └── package.json
    ```
- Deployments can be automated using GitHub Actions Workflow, instead of using a the native AWS CodePipeline. Doing so is recommended because it keeps your CI/CD configuration right alongside the code in your repository. To create this workflow, follow these steps:
    1. Create a `deploy.yml` file at the root of the repository in the following directory: `.github/workflows/deploy.yml`. This script uses AWS OIDC (OpenID Connect) federation, which allows GitHub to safely assume an AWS IAM Role via temporary tokens instead of storing long-lived, high-risk access keys.
    1. AWS OIDC Setup:
        1. Go to IAM > Identity Providers and create an Open ID Connect provider:
            - Provider URL: https://token.actions.githubusercontent.com
            - Audience: sts.amazonaws.com
        1. Create an IAM Role named `GitHubActionsCDKDeployRole` that trusts this provider.
        1. Edit its Trust Relationship policy to explicitly match your repository workspace:
            ```
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Federated": "arn:aws:iam::515424600331:oidc-provider/token.actions.githubusercontent.com"
                        },
                        "Action": "sts:AssumeRoleWithWebIdentity",
                        "Condition": {
                            "StringEquals": {
                                "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                            },
                            "StringLike": {
                                "token.actions.githubusercontent.com:sub": [
                                    "repo:Calvinfr96/dea-wistia-analytics-code-pipeline:*",
                                    "repo:Calvinfr96/dea-crm-lead-assignment-code-pipeline:*"
                                ]
                            }
                        }
                    }
                ]
            }
            ```
            - Adjust the Federated Principal account ID, GitHub username, and repo name (after `repo:`) as needed.
            - For Multiple repositories, list each repository under `"token.actions.githubusercontent.com:sub"` inside an array (not a single string value) using the same format as above.
        1. Attach the `AdministratorAccess` managed policy to this role so it can deploy your architecture resources cleanly.
        1. Ensure you have a clean requirements.txt file at the root of your project directory so the runner container knows exactly what to provision:
            ```
            aws-cdk-lib==2.150.0
            constructs>=10.0.0,<11.0.0

            ```
        1. Once the role is created, update the `role-to-assume` value with the role ARN in the `deploy.yml` file.
- Once the workflow is set up, the `pipeline_stack.py` is no longer needed because GitHub Actions are deploying your AWS resources instead of CodePipeline. The `deploy.yml` file completely replaces this stack.

## GitHub Secrets
- Instead of using Secrets Manager to securely store the Slack Webhook URL, GitHub secrets can be used instead.
    1. Open the **repository** settings, not general account settings.
    1. Under Secrets and variables > Actions, add a new **repository** secret with the appropriate key and value that corresponds to the Lambda handler code.

## AWS CDK
- Prerequisites:
    ```
    brew install node
    node --version
    npm --version

    brew install awscli
    aws configure (IAM user with admin access)

    npm install -g aws-cdk
    cdk --version

    cdk bootstrap aws://YOUR_ACCOUNT_ID/YOUR_AWS_REGION
    cdk init app --language python (from empty project directory)

    source .venv/bin/activate
    pip install -r requirements.txt
    cdk synth
    ```
## AWS S3
- Testing found that the delay between a raw lead being sent to the Raw Data S3 Bucket and updated lead information being sent to the external S3 bucket was closer to 20 minutes, not 10 minutes. This rules out the use of Amazon SQS as a tool to introduce the delay since the maximum delay that can be imposed is 15 minutes.
    - An inefficient workaround to this limitation is to set the SQS delivery delay to the maximum 15 minutes, then introduce a visibility delay of about 6 minutes. This would prevent Lambda from actually seeing the message and executing the script for an additional 6 minutes, introducing a total delay of about 21 minutes. This is inefficient because it introduces idle compute time and the possibility of re-driving failures (where the message fails to be sent to Lambda a second time after the visibility timeout).
    - Since SQS can't be used to introduce the delay, we can't use an Event Notification sent SQS. To properly sync raw data landing in the S3 bucket and raw data being processed by the Lambda, an EventBridge Rule must be created that listens for `Object Created` events in S3, then triggers Step Functions that wait 20 minutes, then trigger the Lambda. These Step Functions are handled by a State Machine.
    - **To properly sync the S3 bucket with EventBridge, this connection must be enabled in the bucket settings.**

## Close API
- API Key: api_4HBHKpUFHpkpAlRws75k6j.6CR8w66s9qfFTqjerFfMda
- Zapier Subscription URL: https://hooks.zapier.com/hooks/catch/28198080/4u89tnq/

## Zapier
- Create and test a Zap that allows data from the webhook to be stored in an S3 bucket
    - Bucket Name: `zapier-webhook-data-calvinfr`.
- The first step in the Zap should be configured as a 'Catch Raw Hook' step.
    - Send a test request via Postman and select it to test the Zap.
- The next step should be configured as a 'Code by Zapier' step. Here, the code from `zapier_scipt.js`, which parses the JSON and extracts the lead ID, needs to be inserted. The lead ID will be used to create a custom file name for the JSON file when it is saved to S3.
    - In the setup, select 'Code by Zapier' as the app and 'Run Javascript' as the action event.
- The last step should be configured as a 'Create Text Object' step. Choose 'Amazon S3' as the app, 'Create Text Object' as the action event, and select `us-east-1` as the region.
    - In the configuration, choose the S3 bucket. In the Key section, type `webhook-data/crm_event_`, then click the `+` button, look for the lead ID under 'Run Javascript in Code by Zapier', select that, the type `.json`. This creates the dynamic file naming.
    - In the content, select 'Full clean JSON'.

## Slack
- Create an App and associated Webhook URL that the Lambda function can use to send out lead notifications to the sales team. This URL can be stored as a secret either in GitHub Secrets or AWS Secrets Manager.
- Once the raw lead data is processed and merged with the updated lead data, it is sent to the a separate S3. The Lambda function that executes this process can also send a message in Slack after the data processing is complete. The Slack message should be formatted as follows:
    ```
    Name:  {display_name}
    Lead ID : {lead_id}
    Created Date: {date_created}
    Label: {status_label}
    Email: {lead_email}
    Lead Owner: {lead_owner}
    Funnel: {funnel}
    ```
    - To avoid spamming a DEA channel or DEA employee with notifications, the webhook is configured to send sales lead notifications to my personal channel as a direct message.
