# Calendly Marketing Insights Project Summary

## GitHub Actions Workflow (AWS CodePipeline Alternative)
- Create a GitHub repository that will be linked with AWS. The repository should store the required Python scripts and configuration files in the following manner:
    ```
    ├── .github/
    │   └── workflows/
    │       └── deploy.yml
    ├── lambda_ingestion/
    │   └── handler.py
    ├── app.py
    ├── cdk.json
    └── requirements.txt
    ```
    - URL: https://github.com/Calvinfr96/dea-calendly-marketing-insights-code-pipeline
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
                                    "repo:Calvinfr96/dea-crm-lead-assignment-code-pipeline:*",
                                    "repo:Calvinfr96/dea-calendly-marketing-insights-code-pipeline:*"
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

## Databricks
- Connect your Databricks account with your AWS account in the AWS Marketplace console.
- Once the account is set up, follow these steps to grant DataBricks permission to access S3:
    1. **Create an IAM Policy:** Create an IAM Policy named `DatabricksS3AccessPolicy` in your AWS Console. This grants Databricks the minimum necessary access to read raw data, manage Auto Loader checkpoint directories, and write output data:
        ```
        {
        "Version": "2012-10-17",
        "Statement": [
            {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:GetBucketLocation",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::calendly-raw-webhook-data",
                "arn:aws:s3:::calendly-raw-webhook-data/*",
                "arn:aws:s3:::calendly-processed-webhook-data",
                "arn:aws:s3:::calendly-processed-webhook-data/*"
            ]
            }
        ]
        }
        ```
    1. **Create a Cross-Account IAM Role:** Create an IAM Role named `databricks-s3-access-role` that Databricks will temporarily be assumed to fetch data. Create the following custom trust policy for the role:
        ```
        {
        "Version": "2012-10-17",
        "Statement": [
            {
            "Effect": "Allow",
            "Principal": { "AWS": "arn:aws:iam::YOUR_AWS_ACCOUNT_ID:root" },
            "Action": "sts:AssumeRole"
            }
        ]
        }
        ```
        1. Attach the `DatabricksS3AccessPolicy` policy to the `databricks-s3-access-role` role.
    1. **Register Storage Credentials in Databricks:** Connect Databricks to the `databricks-s3-access-role` role:
        1. Open your Databricks Workspace and click Catalog in the left sidebar.
        1. Click **Connect > Credentials** and select **Create credential**.
        1. Set **Credential Type** to **AWS IAM Role**.
        1. Provide a name and paste your AWS **Role ARN**.
        1. Click **Create**.
        1. A dialog box will pop up displaying a unique **External ID** and **Databricks AWS Account ID**. **Copy both fields**.
    1. **Finalize the AWS Trust Relationship:** Go back to your AWS IAM Console, open the databricks-s3-access-role, and click **Trust relationships > Edit trust policy**. Update it with the secure credentials Databricks generated for you:
        ```
        {
        "Version": "2012-10-17",
        "Statement": [
            {
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::DATABRICKS_AWS_ACCOUNT_ID:root"
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                "sts:ExternalId": "YOUR_DATABRICKS_GENERATED_EXTERNAL_ID"
                }
            }
            }
        ]
        }
        ```
        - Databricks may also generate an entire custom trust policy, instead of only providing the external ID and AWS account ID. If so, replace the current trust policy with the generated one.
    1. **Map the S3 Path as an "External Location":** Back in the Databricks UI under Catalog Explorer:
        1. Go to **External Data > External Locations** and click **Create location**.
        1. Enter a name.
        1. Set the URL to your raw bucket path (e.g., `s3://calendly-raw-webhook-data`).
        1. Select the storage credential you created in Step 3.
        1. Click **Create**. (**Create an External Location for the raw and processed data buckets**)
- Once Databricks is fully set up, create one notebook for each stage in the medallion architecture. Also create a notebook for weekly maintenance, such as deleting unneeded metadata files in S3.
- Once the notebooks are created, create the jobs and workflows to automate the data pipeline.
    1. Create a `calendly_daily_ingestion` daily ingestion job. This job will handle the sequential processing of data from Bronze to Gold. It should run daily after the third-party marketing spend data becomes available.
        1. Under **Schedules & Triggers**, choose the 'Scheduled' Trigger type, then choose the 'Schedule' Schedule type, then check 'Show cron syntax' and enter the following expression: `0 0 10 * * ?` (Daily at 10:00 AM UTC).
        1. Create an `ingest_bronze` task that doesn't depend on anything. Select the `01_bronze_ingestion` notebook.
        1. Create a `clean_silver` task that depends on the `ingest_bronze` task. Select the `02_silver_cleaning` notebook.
        1. Create an `aggregate_gold` task that depends on the `clean_silver` task. Select the `03_gold_analysis` notebook.
    1. Create a `calendly_weekly_maintenance` job. This job will handle the weekly maintenance.
        1. Under **Schedules & Triggers**, choose the 'Scheduled' Trigger type, then choose the 'Schedule' Schedule type, then check 'Show cron syntax' and enter the following expression: `51 0 0 ? * Sun` (Every Sunday at Midnight UTC).
        1. Create an `optimize_and_vacuum` task that doesn't depend on anything. Select the `table_maintenance` notebook.
    1. For Production environments, make sure to add email alerts and Trigger alerts for job failures or jobs that take longer than expected (30 minutes) to run.

## Streamlit (Visualization)
- The Databricks job saves the final fact tables in S3 in the form of several parquet files. Since the data volume is small, Streamlit is a simpler, more cost-efficient tool to use than Amazon Redshift and Quicksight. Tools such as `duckdb` and `pyarrow` can be used to query data across all parquet files in the S3 directory where the Databricks job is saving the data.
- Create a `streamlit_app.py` file to store all of the logic needed to establish a connection with S3, query the data, and create the dashboards.
- Create an access key for `streamlit-calendly-app-user`. These credentials will be used to add secrets to the Streamlit app, which will allow the app to access S3 once it is deployed.
- Create a `dea-streamlit-calendly-metrics-analytics` Streamlit app:
    - Under Secrets, add the following TOML:
        ```
        AWS_ACCESS_KEY_ID = "<streamlit_user_access_key_id>"
        AWS_SECRET_ACCESS_KEY = "<streamlit_user_secret_access_key>"
        AWS_DEFAULT_REGION = "us-east-1"
        ```

## Data Discovery
- Webhook Data:
    - Top-Level Fields:
        - payload: Calendly Invitee/User object.
        - scheduled_event: Calendly Event object.
    - `event`: The type of event (i.e. `invite.created`).
    - `payload.name`: The name of the invitee.
    - `payload.email`: The email of the invitee.
    - `payload.scheduling_method`: The method used to schedule the event.
    - `payload.timezone`: The timezone of the event.
    - `payload.scheduled_event.created_at`: The time the event was created.
    - `payload.scheduled_event.event_type`: The type of event scheduled (i.e. `facebook_paid_ads`)
    - `payload.scheduled_event.start_time`: The start time of the event.
    - `payload.scheduled_event.end_time`: The end time of the event.
    - `payload.scheduled_event.name`: The name of the event (i.e. 'Data Engineer Academy Info Session').
    - `payload.scheduled_event.event_memberships`: List of event host details (usually only one host).
    - `payload.scheduled_event.location.type`: The type of event location (i.e. virtual (null)/physical).
    - `payload.tracking.utm_campaign`: The campaign associated with the event.
    - `payload.tracking.utm_source`: The source (platform) of the event.
    - `payload.tracking.utm_medium`: The type of input (i.e. cost per click, social media, affiliate, QR code).
    - `payload.tracking.utm_term`: The keywords used in the campaign.
- Spend Data:
    - `date`: The date associated with the record.
    - `channel`: The acquisition channel.
    - `spend`: The total spend for the channel for the given date.
