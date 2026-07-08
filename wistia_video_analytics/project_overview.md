# Wistia Video Analytics Data Pipeline Project

## Overview
This project will use AWS services to build a Continuous Integration and Deployment (CI/CD) pipeline that ingests and analyzes media-level and visitor-level analytics from Wistia's Stats API.
- **Only use AWS Services to build the pipeline**. Use GitHub for CI/CD, Python for API ingestion, and PySpark for data transformation.
- Responsibilities
    - Design the entire system architecture: ingestion, storage, processing, and reporting.
    - Authenticate and ingest data from the Wistia Stats API (both media and visitor level data).
    - Handle pagination and incremental data pulls.
    - Run the pipeline in production for 7 days.
    - Implement CI/CD using GitHub.
    - Document decisions, assumptions, and tradeoffs.

### Architecture Diagram
![](/wistia_video_analytics/project_resources/wistia_data_code_pipeline_v3.png)

## Data Engineering Considerations
- The data pipeline will be handling data in batches, not real-time. The data will be stored in a data warehouse, not a data lake, as we will be working with manageable amounts of semi-structured (JSON) data, not large amounts of unstructured data.
    - Since the data is semi-structured, an ETL process will be used to handle the data instead of ELT.
- Business requirements:
    - Design an automated, CI/CD data pipeline that ingests media and visitor data from Waistia's Stats API.
- To build a CI/CD data pipeline, we need to take advantage of AWS CodePipeline, which transfers files from a GitHub repository to an S3 bucket. From the S3 bucket, we can use various services to ingest transformation code from the repo and implement ETL logic.
    1. Amazon Managed Workflows for Apache Airflow
        - Works as an orchestrator that schedules separate execution tasks, connecting with AWS services such as S3, Glue, SageMaker, and EMR.
    1. AWS Glue (Serverless ETL)
        - Upload Apache Spark scripts (Python/PySpark or Scala) directly into the glue job.
        - Best used with large-scale, distributed big data transformations, processing large quantities of data across structured and unstructured sources.
        - Completely serverless with an integrated Glue Data Catalog to map schemas automatically.
    1. AWS Lambda (Event-Driven Serverless Compute)
        - Ingests scripts (Python, Node JS, Java, or Go) bundled up as a zip file or container image.
        - Best used for light weight, real-time data adjustments, transforming data in-flight as it arrives.
        - Low-latency and cost effective for smaller files. Data must be capable of being processed in less than 15 minutes.
    1. Amazon EMR Serverless (Big Data Frameworks)
        - Ingests applications built on Apache Spark, Hive, or Presto packages hosted in S3.
        - Best used for petabyte-scale transformations or machine learning engineering that requires precise control over runtime dependencies.
    1. Amazon Managed Service for Apache Flink
        - Runs continuous streaming SQL queries or Java/Python applications directly over real-time event feeds.
        - Best used for real-time, continuous data enrichment, anomaly detection, or tumbling-window metric aggregations on a data stream.
        - Best used for applications that require ingesting data in real-time on live event streams, rather than ingesting data in micro batches or macro batches.
- Options that are best for daily, small volume data ingestion
    1. AWS Glue Spark **(Recommended for PySpark)**
        - AWS Glue natively supports PySpark scripts out of the box. For small daily files, a generic multi-node configuration wastes money on cluster setup, latency, and idle compute. The following optimizations can be made for minor workloads:
            - Configure the Glue Job to run on Glue 4.0 or higher.
            - Use the G.1X worker type and set the maximum number of workers to 2 DPUs.
            - Enable auto-scaling.
            - Define a static schema within your script, instead of allowing Spark to infer the schema (requires an expensive full pass over the data).
            - If the Glue Job can execute in less than 1 minute, it is free. Otherwise, you are billed by the second.
            - Job Bookmarks can be used to automatically track state and only process fresh data arriving each day.
    1. AWS Lambda (Alternative for Cost Savings)
        - AWS Lambda **does not natively run PySpark** because running local Spark requires a Java Virtual Machine (JVM) environment that vastly exceeds Lambda's lightweight design.
        - Instead of PySpark, your Python script can be packaged using Pandas or DuckDB. This allows the script to start up in milliseconds, costs fractions of a cent per execution, and requires zero cluster configuration.
        - **Script must complete within Lambda’s 15-minute runtime ceiling.**
- Conclusion:
    - Considering PySpark is a requirement for implementing the ETL logic, building an AWS Glue CodePipeline would be the best approach. Building the pipeline using Lambda as an extraction tool and Glue as a transformation and loading tool also improves scalability if the pipeline needs to handle transformation of vast amounts of raw data. Using separate Lambda functions for extraction, transformation, and loading would limit execution time for transformation and loading to 15 minutes.

## System Design Considerations
- Target Database: S3
    - Provides simple and scalable storage of raw and processed data at low cost.
- Data Extraction/Ingestion: Lambda
    - A Lambda function will be used to extract the data from the Wistia API and load it into an S3 bucket. Lambda is being used because it provides low-cost serverless compute.
    - Extracting manageable amounts of JSON data from the API once per day falls well within Lambda's 15-minute execution time limit.
- Data Transformation: Glue
    - A Glue ETL Job will be created to transform raw JSON data, enforcing a strict schema and applying necessary transformations and aggregations.
    - Enforcing a strict schema saves compute time by preventing Spark from inferring schema by repetitively scanning the JSON data.
    - Extraction could also be performed in the Glue ETL job, but this is not recommended for several reasons:
        - Doing so violates engineering principles, such as separation of concerns, by combining extraction, transformation, and loading into a single script.
        - Calling the API and waiting for a response wastes compute resources that could be more efficiently utilized using Lambda.
        - Spark scripts execute sequentially on the driver node, ignoring the rest of the cluster capacity. If a job is parallelized across many nodes, it could potentially trigger API rate limiting, which will crash the entire job.
        - Loss of data lineage by extracting and transforming raw data in one step.
- Data Loading: Glue
    - The PySpark script that transforms the raw JSON data will also load it into S3.
- Scheduling Mechanism:
    - Amazon EventBridge will be used to schedule the Lambda to extract JSON data from the API once a day.
    - S3 event notifications will be used to trigger the Glue Job when new, raw JSON data lands in S3.
    - The Glue ETL Job can also be scheduled using a Glue Trigger, but an S3 Event Notification more practically syncs the data extraction phase with the transformation and loading phases.
- CI/CD and Dev Ops: AWS CodePipeline and CodeBuild
    - Seamlessly integrates with GitHub and automatically updates infrastructure, ingestion scripts, and transformation scripts whenever a commit is pushed to the source repository.
- Error Handling:
    1. Inside the custom wistia_ingest.py script, explicit error handling checks for HTTP status codes. If Wistia is down (e.g., HTTP 500) or rate-limiting the API token (HTTP 429), the code throws an explicit Python Exception. This forces the Lambda function to fail visibly so it can be retried.
    1. The PySpark script handles structural issues by enforcing a strict schema (wistia_schema). If a daily JSON drop contains corrupted structures or invalid formatting, Spark will isolate the damaged rows into a column of null values or fail the run entirely depending on your read mode. This protects downstream analytics from corrupted data entry.
    1. You can attach a Dead Letter Queue (DLQ) using Amazon SQS to the EventBridge rule. If an event cannot be delivered to Glue after 24 hours of retries, it is deposited into the SQS queue so you don't lose the event trigger.
- Retries:
    1. When triggered by an Amazon EventBridge cron schedule, if the Lambda function crashes due to a network timeout or an unhandled exception, EventBridge automatically retries the execution up to 2 times by default.
    1. AWS Glue jobs feature built-in retry mechanics managed via the job configuration. In the CloudFormation setup, a MaxRetries property can be set (e.g., MaxRetries: 1). If a cluster node fails or an underlying network interruption occurs, Glue will cleanly provision a brand-new container cluster and run the code again from scratch.
    1. When a raw data file lands in S3, EventBridge attempts to notify the AWS Glue API to run the transformer job. If the AWS Glue API is experiencing an outage or throttling, EventBridge automatically retries invoking the API using an exponential backoff algorithm for up to 24 hours.
- Logging:
    1. Any standard print() statement or native Python logging command streams execution metrics automatically into Amazon CloudWatch Logs under the log group /aws/lambda/wistia-api-extractor.
    1. AWS Glue natively splits its execution tracking into two distinct stream destinations inside CloudWatch:
        1. The Job Output Log stores standard execution print outputs and script tracking messages.
        1. The Job Error Log Isolates the pure Java, Scala, or Python stack traces, allowing developers to immediately find the exact line numbers that broke the computation.

## Resources
- Requirements: https://docs.google.com/document/d/1Ezv3heaRtzmTBTkD2USskV21NoDKyX3pDZGAe3_OJw8/edit?tab=t.0
- Wistia API Documentation: https://docs.wistia.com/reference/get_stats-medias-mediaid