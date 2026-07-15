# Calendly Marketing Insights Project

## Overview
This project will use AWS services to build an automated data engineering pipeline for an organization and create business insights using **marketing** and **Calendly** data. The first goal is to gain an understanding of marketing efforts and leads generated per marketing campaign. This helps manage marketing budgets and gain insights into the conversion rate of each campaign. The second goal is to gain a better understanding of meeting schedules in order to better optimize calendars.
- Objectives:
    1. Manually analyze the JSON data sets of webhooks and determine the input needed.
    1. Manually identify the JSON data elements to determine the table structures needed for designing the Bronze, Silver, and Gold layers of Calendly data.
        - Similar to the Lead Assignment and Notification System, a webhook subscription URL needs to be created to receive data from the Calendly API and send it to a destination such as S3.
        - **BLOCKER: Send the API URL to an SME (Avirup/Azmat/Ninad/Kareem) for Webhook creation.**
        - **AWS Services should be used to create the subscription URL.**
    1. Once the webhook subscription is set up and data is being received from Calendly, look for the following properties in the JSON:
        - `event_type`: Helps identify the marketing campaign’s events.
        - `event_name`: Helps identify the marketing events from the pool of all events.
        - `event`: Look specifically for the `invitee.created` event.
        - `payload`: Flatten the payload data and prepare a table to join with the marketing data based on date.
    1. Analyze data for total spend that will be used to produce a ‘Cost Per Booking (CPB) by Channel’ dashboard.
        - The data will be present in a public S3 bucket at 06:00 EST daily for Day-1 spends. Data in the file includes marketing data for a maximum time period of 30 days.
        - The data can be accessed dynamically using the following URL: `https://dea-data-bucket.s3.us-east-1.amazonaws.com/calendly_spend_data/spend_data_YYYY-MM-DD.json`
            - The JSON data includes information on the channel and the total daily spend (USD).
        - The following URL can be used to check for available files within this bucket: https://dea-data-bucket.s3.us-east-1.amazonaws.com/calendly_spend_data/file_index.json
            - Spend data seems to be available for the previous month.
- Required Metrics:
    1. Daily Calls Booked by Source: Count of Calendly bookings per source (Google, Facebook, YouTube, etc.) per day.
    1. Cost per Booking (CPB) by Channel: Determine how much it costs to acquire a lead in each marketing channel.
        1. This identifies the most cost-efficient acquisition channels.
        1. Formula: Cost per Lead = Total Spend / Total Booked Calls
        1. Group by channel, then compute cost per lead.
    1. Booking Trend Over Time: Track the daily/weekly volume of Calendly bookings per source.
        1. This identifies trends like campaign fatigue, seasonal changes, or impact of new creatives.
        1. Group bookings by date and source, then plot counts over time.
    1. Channel Attribution: Attribute bookings to specific marketing channels or campaigns using UTM  parameters.
        1. This identifies which sources and campaigns generate the most and cheapest calls.
            1. Group bookings by source, then calculate the following:
                1. Total bookings
                1. Total spend
                1. CPB
                1. Sort and visualize in a leaderboard or heatmap.
    1. Booking Volume by Time Slot / Day of Week: Understand when leads prefer to book calls.
        1. Helps with resource planning and scheduling ad delivery.
        1. Extract the hour and day_of_week from Calendly booking timestamps and plot heatmaps or histograms grouped by time and channel.
    1. Meeting Loads per Employee: Calculate how many meetings each employee attends weekly.
        1. Identifies potential burnout or over-scheduling.
        1. Formula: Average Meetings per Week = Total Meetings / Number of Weeks
        1. Group by employee_id
- Deliverables:
    1. Daily Calls Booked by Source: Count of Calendly booking by source per day.
        1. Monitors daily performance and compares lead generation efforts across channels.
        1. Line Chart: Date vs. Number of Bookings (color-coded by source).
        1. Optional: Daily comparison channel by source.
    1. Cost per Booking (CPB) by Channel: Calculate average cost per booking by channel.
        1. Reveals most cost-effective channels for acquiring leads.
        1. Formula: CPB = Total Spend / Total Booked Calls
        1. Bar Chart: Channel vs. CPB.
        1. KPI Tiles: Total Bookings, Total Spend, Average CPB.
        1. Tables With Sorting: Channel, Spend, Bookings, CPB.
        1. Data Requirements: channel, spend, booking_id.
    1. Bookings Trend Over Time: Track daily/weekly booking volume by source.
        1. Identifies dips, surges, or patterns due to campaigns, seasonality, or other factors.
        1. Line Chart: Date vs. Number of Bookings by Source.
        1. Area Chart: Cumulative Bookings.
        1. Data Requirements: booking_date, source, booking_id.
    1. Channel Attribution (CPB and Volume Leaderboard): Attribute bookings to channels using UTM parameters and rank by volume and cost.
        1. Allows precise ROI tracking by source.
        1. Leaderboard Table: Source, Total Bookings, Spend, CPB.
        1. Heatmap: CPB by Channel and Campaign. (**UTM campaign data is not sufficient enough to create this visualization.**)
        1. Bar Chart: Top-performing sources by bookings.
        1. Data Requirements: source, campaign, booking_id, spend.
    1. Booking Volume by Time Slot / Day of Week: Determine booking activity patterns across time slots and weekdays.
        1. Informs ad scheduling and team resource planning.
        1. Heatmap: Hour of Day vs. Day of Week (intensity = bookings).
        1. Histogram: Bookings by Hour.
        1. Pie Chart: Bookings by Day of Week.
        1. Data Requirements: booking_timestamp, source, booking_id.
    1. Understand Meeting Load per Employee: Show how many meetings each employee attends per week.
        1. Helps track workload and prevent scheduling overload.
        1. Formula: Average Meetings per Week = Total Meetings / Number of Weeks
        1. Bar Chart: Employee vs Average Meetings per Week.
        1. KPI: Total Meetings, Maximum Meetings, Minimum Meetings.
        1. Optional Line Chart: Weekly trend per employee.
        1. Data Requirements: employee_id, meeting_id, meeting_date.

**Stramlit App URL:** https://dea-calendly-metrics-analytics-calvinfr.streamlit.app/

**Streamlit App Repo:** https://github.com/Calvinfr96/dea-streamlit-calendly-metrics-analytics

### Architecture Diagram
![](/calendly_marketing_insights/project_resources/calendly_marketing_insights_pipeline_v2.png)

## Data Engineering Considerations
- The data pipeline will be handling manageable amounts of data in real-time. The data will be stored in a data warehouse, not a data lake, as we will be working with manageable amounts of semi-structured (JSON) data, not large amounts of unstructured data.
    - Since the data is semi-structured, an ETL process will be used to handle the data instead of ELT.
- Business requirements:
    - Design an automated data pipeline that receives and stores raw calendar information, then merges it with daily spending data.
- To build the data pipeline, we can take advantage of GitHub Actions Workflow, AWS Open ID Connect (OIDC), and AWS Cloud Development Kit (CDK). Doing so allows us to write our infrastructure as code, instead of manually creating it. This vastly improves maintainability.
- Establishing a connection with Calendly Webhook requires creating a subscription URL with API Gateway. When this URL receives event data from the webhook, it processes it using a Lambda function and sends the data to an S3 bucket. Lambda is used because it is a serverless, lightweight compute service that can easily handle parsing incoming JSON data and storing it in S3 in raw format.

## System Design Considerations
- Target Database: S3
    - Provides simple and scalable storage of raw and processed data at low cost.
- Data Extraction/Ingestion: API Gateway and Lambda
    - The webhook will send a `POST` request, containing the relevant event data, to the API's `/webhook` route. The API is integrated with a Lambda function that will parse the data and save it to S3 in raw format.
- Data Transformation/Loading: DataBricks
    - DataBricks will be used to transform the raw data using the Medallion architecture, then send the transformed data to S3 for analysis.
- Scheduling Mechanism:
- CI/CD and Dev Ops: GitHub Actions
    - Seamlessly integrates with AWS and automatically updates infrastructure, ingestion scripts, and transformation scripts whenever a commit is pushed to the source repository.
- Error Handling:
- Retries:
- Logging:

## Resources
- Requirements: https://docs.google.com/document/d/1CEm_lQy5hlCIcJqE7TmCtqF_NuYAqngm/edit
- Calendly API Docs: https://developer.calendly.com/api-docs/4b402d5ab3edd-calendly-developer
- Lakehouse Architecture Overview: https://www.geeksforgeeks.org/lambda-architecture-vs-kappa-architecture-in-system-design/
