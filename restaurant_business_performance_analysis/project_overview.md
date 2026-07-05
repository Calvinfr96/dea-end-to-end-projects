# Restaurant Business Performance Analysis Project

## Overview
This project will use AWS services to build a unified data view that facilitates understanding of customer behavior, spending patterns, and overall business performance across all restaurant locations and platforms. The system should perform the following functions:
- Calculate and update Customer Lifetime Value (CLV) daily.
- Classify customers into high, medium, and low value groups.
- Segment customers using recency, frequency, and monetary (RFM) metrics.
- Identify customers at risk of churn.
- Highlight daily/weekly/monthly sales trends and seasonal patterns.
- Compare the performance of loyalty members versus non-members.
- Identify the best- and worst-performing locations.
- Identify the impact of discounts or promotions on revenue and profitability.

Design a pipeline architecture for ingesting, transforming, and storing data. Design a production level pipeline that includes scheduling, encryption, failure reload mechanism. Insights should be accessible through an interactive dashboard that supports data-driven marketing, operational, and strategic decisions. The architecture should support the following requirements:
- Use SQL Server as a source to pull data from the database.
- Designed primarily using AWS resources.
- Implement logic using PySpark.

**Stramlit App URL:** https://dea-restaurant-metrics-analytics-calvinfr.streamlit.app/

**Streamlit App Repo:** https://github.com/Calvinfr96/dea-streamlit-restaurant-metrics-analytics

## Metrics and Required Insights
- Customer Lifetime Value (CLV):
    - The total projected revenue or net profit a business expects to earn from a single customer throughout their entire relationship.
    - CLV helps companies understand customer value, optimize acquisition costs, and prioritize long-term retention over short-term sales.
    - CLV = Average Order Value * Purchase Frequency * Customer Lifespan
    - For example, if a customer spends an average of $100 per purchase and makes a purchase once every six months, with a retention time of five years, the CLV would be: CLV = ($100) * (2 purchases per year) * (5 years) = $1,000.
    - Data model should show how CLV evolves on a daily basis for each customer.
    - CLV values should be grouped as follows:
        - High CLV: Top 20% customers
        - Medium CLV: Mid 60%
        - Low CLV: Bottom 20%
- Recency, Frequency, and Monetary Logic:
    - Group customers based on spending and activity to support campaign targeting.
    - Recency: Days since last purchase
    - Frequency: Number of purchases in last N months
    - Monetary: Total spend in last N months
    - Customers should be grouped as follows:
        - VIPs: High R, F, M
        - New Customers: Low F, high R
        - Churn Risk: Low R, low F
- Churn Indicators:
    = Build a customer activity profile to help marketing identify at-risk customers without using predictions. This allows analysts to take retention actions in a timely manner.
    - For each customer, compute:
        - Days since last order
        - Average gap between orders
        - Percentage change in spending over N periods
    - Customers should be tagged as "at-risk" based on an inactivity threshold, such as no orders in the last 45 days,
- Sales Trend Monitoring:
    - Generate time-based summaries to analyze sales patterns. This helps identify peak periods and plan resources accordingly.
    - Aggregate daily, weekly, and monthly order revenue. Break down sales figures by:
        - Location
        - Menu category
        - Time of day
        - Whether the day is a holiday
- Loyalty Program Impact:
    - Compare loyalty members vs non-members in terms of spend and engagement. This helps with evaluating the ROI of the loyalty program.
    - Filter orders based on the customer's status as a loyalty member. Compare the following per customer:
        - Average spend
        - Repeat orders
        - Lifetime value
- Location Performance:
    - Identify best and worst-performing store locations. This will help make decisions about promotions, staffing, and expansion.
    - Group order items by location or store ID and calculate the following:
        - Total revenue
        - Average order value
        - Orders per day/week
    - Rank locations based on revenue.
- Pricing and Discount Effectiveness:
    - Measure how discounts affect revenue and profitability. This helps analysts optimize pricing strategies.
    - Use `order_item_options.option_price` to detect discounts (option_price < 0). Compare the following:
        - Revenue from discounted vs non-discounted orders.
        - No items were discounted during the data collection period.

## Data Engineering Considerations
- Data pipeline will be handling data in batches, not real-time. The data will be stored in a data warehouse, not a data lake, as we will be working with manageable amounts of structured (CSV) data, not large amounts of unstructured data.
    - Since the data is structured, an ETL process will be used to handle the data instead of ELT.
- Business requirements:
    - Analyze restaurant business performance metrics in order to build insights that support data-driven marketing, operational, and strategic decisions.

## System Design Considerations
- Since data will be handled in batches instead of real-time, eventual consistency is acceptable, while strong consistency is not a strict requirement. Restaurant business metrics won't be analyzed frequently enough for data consistency to be a major issue.
- Availability and partition tolerance are important for reliably analyzing data as it is extracted from its source in batches.
- AWS S3 serves as a cost-effective storage solution for both raw and processed data.
- AWS Athena serves a convenient way to query and analyze processed data, due its serverless architecture.

### Architecture Overview
- Amazon RDS:
    - Stores restaurant order and sales data uploaded locally using SQL server.
- Amazon S3 will be used to store data using the Medallion architecture to ensure reliability and performance. Data will be stored in the following zones based on level of transformation:
    - Bronze Layer: Append-only copy of raw data partitioned by ingestion date.
    - Silver Layer: Schema enforcement, null handling, data deduplication, and data type casting, partitioned by order date.
    - Gold Layer: Star-schema dimensional model optimized for BI queries.
- AWS Glue will be used for serverless orchestration and scheduling. The Glue workflow will consist of three jobs:
    - Job 1: Ingest to Bronze.
    - Job 2: Clean to Silver.
    - Job 3: Compute Gold Models.
    - Using AWS Glue instead of Amazon EMR and Apache Airflow reduces operational overhead and simplifies pipeline maintenance.
    - AWS DMS serves as a good alternative for real-time tracking and Change Data Capture.
- Scheduling & Automation:
    - Instead of managing an Airflow environment, pipeline orchestration is handled entirely with AWS Glue workflows.
    - A time-based Glue Trigger can be used to start the workflow on a daily basis. Each subsequent job only runs if the preceding job returns a status of `SUCCEEDED`.
- Failure Reload and Error Handling:
    - AWS Glue provides built-in mechanisms to ensure resilience and automatic recovery without data duplication. To prevent data duplication during a job re-run, Glue uses Delta Lake's ACID transaction properties. Instead of basic appends, the Gold layer will use a `MERGE INTO` statement to update existing records matching the execution date.
    - Each AWS Glue ETL Job is configured with a `Max Retries` setting of 2. If a transient network glitch or connection error occurs with RDS, Glue restarts the job automatically.
    - An Amazon EventBridge rule can be set up to monitor Glue Workflow states. If any job transitions to `FAILED`, EventBridge can route the alert to an Amazon SNS topic, which can alert an engineer who can assess the issue.
- Network Security & Data Catalog Integration:
    - Native Glue connections are configured with VPC routing enabled. This places Glue worker nodes securely inside the private subnets of your VPC so they securely communicate with the RDS SQL Server to retrieve data.
    - Instead of manually running Glue Crawlers after every run, which can be costly, the Gold ETL job can be configured to update the AWS Glue Data Catalog directly at the end of the script using Delta Lake manifest generation or Spark SQL catalog sync. This makes the new data instantly visible to Amazon Athena and Amazon QuickSight.

### Dashboard Requirements
- Customer Segmentation:
    - What distinct customer segments emerge when grouping customers by purchase behavior (total spend, frequency, recency) and loyalty status?
    - Visualize segmentation (e.g., via RFM scores) to enable targeted marketing.
- Churn Risk Indicators:
    - Which metrics, such as days since last order, average order interval, and spend trends, correlate with a higher churn risk?
    - Highlight threshold-based alerts (e.g., customers at risk) to prompt re-engagement actions.
- Sales Trend and Seasonality:
    - What are the monthly and seasonal trends in sales, and how do these vary by product category or location?
    - Track weekly/monthly sales aggregates and holiday spikes to support inventory planning and staffing decisions.
- Loyalty Program Impact:
    - How does loyalty membership affect customer spending and repeat order rates?
    - Compare key metrics (CLV, average order value, repeat purchase rate) between loyalty and non-loyalty customers to assess program effectiveness and inform potential adjustments.
- Location Performance:
    - Which restaurant locations generate the highest revenue, and what operational metrics (e.g., average order size, customer retention) distinguish top performers?
    - Rank locations and highlight actionable insights for expansion or targeted improvements.
- Pricing and Discount Effectiveness:
    - How are discounts and promotions affecting overall sales volume and net revenue?
    - Compare revenue and profit (gross versus net after discount adjustments) for discounted versus full-price transactions to refine pricing strategies.
    - **No items in the data set have been discounted.**

## Resources
- Requirements: https://docs.google.com/document/d/1F6H4RQbtr-nXul8sptK87i-USxVns_AQ/edit
- Order Items Data: https://drive.google.com/file/d/1GXRZNgfngU6Yal6hzs5NClDgJoN3vEKZ/view?usp=drive_link
- Order Item Options Data: https://drive.google.com/file/d/1l9anZqzpgTsQXe1ZTg-ihhn-9SBsa2H_/view?usp=drive_link
- Date Dimension Table: https://drive.google.com/file/d/1v1rPl4nJp1B_nQmNm_Nrz2ZeBkppKRYh/view?usp=drive_link
- SQL Server Upload Tutorial: https://drive.google.com/file/d/10-YApwQA5rsO8s4dcSzI82BU_y4pLPDe/view?usp=drive_link