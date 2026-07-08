# Wistia Video Analytics Data Pipeline Project Summary

## GitHub
- Create a GitHub repository that will be linked with AWS CodePipeline. The repository should store the required Python scripts and configuration files in the following manner:
    ```
    wistia-pipeline/
    ├── infra/                  # IaC Definitions (CDK or Terraform)
    │   ├── app_stack.py        # Lambda, S3 buckets, Glue, Secrets, Athena
    │   └── pipeline_stack.py   # CodePipeline, CodeBuild, CloudFormation deployer
    ├── src/
    │   ├── ingestion/
    │   │   └── lambda_function.py  # Python Ingestion Script
    │   └── transformation/
    │       └── glue_job.py          # PySpark Transformation Script
    └── README.md
    ```
    - URL: https://github.com/Calvinfr96/dea-wistia-analytics-code-pipeline
    - An infrastructure as code (IaC) approach will be used to create the pipeline using AWS Cloud Development Kit (CDK). AWS CDK is highly recommended here because it builds a AWS-native CI/CD pipeline (`CodePipeline`) that needs to dynamically synthesize and deploy other stacks.
- Once the GitHub repository is created. Establish a connection with AWS by navigating to the AWS Console > Developer Tools > Settings > Connections, then creating a connection with GitHub.
    - Follow the UI prompts to install the AWS connector app on your repository.
    - Copy the resulting connection ARN: `arn:aws:codestar-connections:region:account:connection/id`.
    - Using  GitHub connection is a more secure way of granting CodePipeline access to your repository because it doesn't require you to store a personal access token in Secrets Manager. You can also configure AWS GitHub App connection to only have access to specific repositories, instead of the entire account.
    - The GitHub Connection is also specified as a generic ARN, rather than a sensitive security token. This makes it easier to share amongst team members.

### GitHub Actions Workflow (AWS CodePipeline Alternative)
- Deployments can be automated using GitHub Actions Workflow, instead of using a the native AWS CodePipeline. Doing so is recommended because it keeps your CI/CD configuration right alongside the code inside your repository. To create this workflow, follow these steps:
    1. Create a `deploy.yml` file at the root of the repository in the following directory: `.github/workflows/deploy.yml`. This script uses AWS OIDC (OpenID Connect) federation, which allows GitHub to safely assume an AWS IAM Role via temporary tokens instead of storing long-lived, high-risk access keys.
    1. AWS OIDC Setup:
        1. Go to IAM > Identity Providers and create an Open ID Connect provider:
            - Provider URL: https://token.actions.githubusercontent.com
            - Audience: sts.amazonaws.com
        1. Create an IAM Role name `GitHubActionsCDKDeployRole` that trusts this provider.
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
                                "token.actions.githubusercontent.com:sub": "repo:Calvinfr96/dea-wistia-analytics-code-pipeline:*"
                            }
                        }
                    }
                ]
            }
            ```
            - Adjust the Federated Principal account ID, GitHub username, and repo name (after `repo:`) as needed.
        1. Attach the `AdministratorAccess` managed policy to this role so it can deploy your architecture resources cleanly.
        1. Ensure you have a clean requirements.txt file at the root of your project directory so the runner container knows exactly what to provision:
            ```
            aws-cdk-lib==2.150.0
            constructs>=10.0.0,<11.0.0

            ```
        1. Once the role is created, update the `role-to-assume` value with the role ARN in the `deploy.yml` file.
- Once the workflow is set up the `pipeline_stack.py` is no longer needed because GitHub Actions are deploying your AWS resources instead of CodePipeline. The `deploy.yml` file completely replaces this stack.

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

## Data Discovery
1. Media Stats API (JSON Object):
    1. **Required Path Parameter: mediaId (string) - The hashed ID or ID of the video for which you want to retrieve stats.**
    1. load_count (int) - The total number of times this video has been loaded.
    1. play_count (int) - The total number of times this video has been played.
    1. play_rate (float) - The percentage of visitors who clicked play (between 0 and 1).
    1. hours_watched (float) - The total time spent watching this video.
    1. engagement (float) - The average percentage of the video that gets viewed (between 0 and 1).
    1. visitors (int) - The total number of unique people that have loaded this video.
    1. actions (object)
        1. type (string) - Type of action (e.g., "Call to Action").
        1. action_count (int) - Number of actions performed.
        1. impression_count (int) - Number of times the action was shown.
        1. Rate (float) - The rate of actions performed over impressions.
        1. url (string) - For action types that link out (e.g., post-roll CTA), the URL the viewer was directed to.
        1. text (string) - For action types that include display text (e.g., post-roll CTA), the text shown to the viewer.
1. Media Stats by Date API (JSON Object Array):
    1. **Required Path Parameter: mediaId (string) - The hashed ID or ID of the video for which you want to retrieve stats.**
    1. **Query Parameters: start_date, end_date**
    1. date (date) - The date the statistics were taken.
    1. load_count (int) - The total number of times this video has been loaded.
    1. play_count (int) - The total number of times this video has been played.
    1. hours_watched (int) - The total number of hours this video has been watched.
1. Media Engagement API (JSON Object):
    1. **Required Path Parameter: mediaId (string) - The hashed ID or ID of the video for which you want to retrieve stats.**
    1. engagement (float) - The percentage of the video that was viewed, averaged across all viewing sessions.
    1. engagement_data (int array) - An array for creating an engagement graph.
    1. rewatch_data (int array) - An array for creating the rewatch block on an engagement graph.
1. List Visitors API (JSON Object Array):
    1. **Query Parameters: page, per_page, filter, search**
    1. visitor_key (string) - A unique identifier for the visitor.
    1. create_at (timestamp) - When the visitor was created.
    1. last_active_at (timestamp) - The last time the visitor played a video.
    1. last_event_key (string) - The event key for the last video play action.
    1. load_count (int) - The total number of videos loaded by the visitor.
    1. play_count (int) - The total number of videos played by the visitor.
    1. visitor_identity (object)
        1. name (string)
        1. email (string)
        1. org (object)
            1. name (string)
            1. title (string)
    1. user_agent_details (object)
        1. browser (string)
        1. browser_version (string)
        1. platform (string)
        1. mobile (boolean)
1. Show Visitor API (JSON Object):
    1. **Required Path Parameter: visitorKey (string) - The unique key of the visitor.**
    1. visitor_key (string)
    1. created_at (timestamp)
    1. last_active_at (timestamp)
    1. last_event_key (string)
    1. load_count (int)
    1. play_count (int)
    1. visitor_identity (object)
        1. name (string)
        1. email (string)
        1. org (object)
            1. name (string)
            1. title (string)
    1. user_agent_details (object)
        1. browser (string)
        1. browser_version (string)
        1. platform (string)
        1. mobile (boolean)
- Notes:
    - Media Stats API  and Media Engagement API show overall watch statistics for a given media ID.
    - Media Stats by Date API shows stats for previous day and current day when start and end dates aren’t specified.
    - Media Stats by Date API has optional query parameters for start and end date.
        - When both are specified, the response is an array of response objects, one for each day in the time period (inclusive).
        - When only start date is specified, the response is an array of response objects, one for each day from the start date to the current date (inclusive).
        - Statistics for the current date always seem to be zero. Better to query for a time period up to the previous day.
    - List Visitors API Query Parameters:
        - page (int) - The page of results based on the per_page parameter.
        - per_page (int) - The maximum number of results to return, capped at 100.
        - filter (string enum) - Filtering parameter to narrow down the list of visitors.
            - has_name
            - has_email
            - identified_by_email_gate
        - search (string) - Search for visitors based on name or email address.
            - Most users seem to be anonymous. Not worth searching for a particular name or email.
        - List Visitors is easier to use because Show Visitor requires a specific visitor key to be put into the path.
        - To find video engagement across Facebook and YouTube, filter objects in the response based on the following condition:
            - user_agent_details.browser = ‘Facebook’ OR user_agent_details.browser = ‘YouTube’ (Most available data seems to be for Facebook)
    - Implementation:
        - Since the Media Stats API and Media Engagement API represent aggregated data, we could use an SCD2 table to ingest historical aggregate data.
        - APIs to exclude from analysis:
            - Media Stats by Date API (Shows historical **daily** media statistics. Not needed for daily ingestion of cumulative media stats.)
            - Media Engagement API (Media Stats API contains all relevant aggregate data).
            - Show Visitor API (Requires a unique visitor key as a path parameter).
            - Data seems to be updated on a daily basis. There’s only a need to call the API once a day when ingesting data.
        - Other Useful APIs:
            - Show Media Analytics
            - Show Media Analytics Time Series
