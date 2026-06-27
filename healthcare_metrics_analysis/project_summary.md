# Healthcare Metrics Analysis Project Summary

## AWS S3
- Create a `healthcare-data-analysis-calvinfr` bucket that will store the raw and processed healthcare data.
    - Create a `raw-csvs` folder to store the raw CSV data. Data will be uploaded to this folder based on the date as follows: `s3://[bucket-name]/raw-csvs/YYYY/MM/DD/file.csv`.
    - A `tables` folder will be created to store the CSV data in parquet format, after it has been processed by the Lambda function.
    - Create a `error-quarantine` folder that will store malformed CSV data.
    - Create a `query_results` folder to store Athena query results.
- Once the bucket is created, create an event notification for the `raw-csvs` folder, setting the destination to the lambda function. This will execute the lambda function each time a file is created (uploaded).
    - Set the S3 prefix as `raw-csvs/`.
    - Set the S3 suffix as `.csv`

## AWS IAM
- Create an `s3-uploader` IAM User with the permissions needed to upload objects to an S3 bucket.
    - Create an access key to configure the local AWS CLI with the permissions needed to uploaded files to S3.
    - Copy the access key credentials and use them in the `aws configure` command.

## AWS Lambda
- Create a `healthcare-data-analysis` lambda function using the following settings:
    - Runtime: Python 3.14
    - Create a custom execution role (a previously existing role can also be used)
- Once the function is created, adjust the general configuration as follows:
    - Memory: 3000 MB
    - Ephemeral Storage: 3000 MB (a CSV file can expand to more than 3 times its size when loaded completely into memory as a Pandas DataFrame)
    - Timeout: 5 min
- Ensure the Lambda execution role (created with the function) has the following permissions:
    - AmazonS3FullAccess
    - AWSGlueServiceRole
- Ensure the Lambda function has the following environment variables:
    - Key: `PROCESSED_BUCKET_NAME`
    - Value: `healthcare-data-analysis-calvinfr` (bucket name, not URI)
- Add a layer to the lambda function, choosing the following settings:
    - AWS Layers: AWSSDKPandas-Python314 (matches python version of function)
    - Version (the most up to date version)
    - Using the AWS-managed layer is better than building a custom layer because the managed layer includes all dependencies (pandas and pyarrow) needed to efficiently write the CSV data to parquet format.

### Lambda Troubleshooting
- Ran into UTF-8 encoding issues while parsing a file.
    - Saved file as a `.txt` file with the UTF-8 format.
    - Re-saved as CSV file.
    - Re-uploaded file to S3 and the function executed properly.
- Athena will be used to query the parquet files processed by the Lambda function. Since each file uploaded to the S3 bucket represents a different table, the Lambda function needs to be updated to push files into a directory derived from the file name.
    - Old Path Strategy: `s3://processed-bucket/processed-data/year=2026/...`
    - New Path Strategy: `s3://processed-bucket/tables/[table_name_derived_from_file]/year=2026/...`
    - This new strategy is required because Athena tables map to S3 folder prefixes, not directly to individual file names.

## Amazon Athena
- Create a `healthcare_data_analytics` database with the following DDL: `CREATE DATABASE IF NOT EXISTS healthcare_data_analytics;`
    - The tables in Athena will be created in this database automatically by the Lambda function.
    - The tables are being created in the Lambda function because each CSV file uploaded has a different schema. If the CSV files had one schema, one table with a unifying schema could be created directly in Athena.
        ```
        -- 1. Create a dedicated database if you don't have one already
        CREATE DATABASE IF NOT EXISTS operational_analytics;

        -- 2. Switch to your database context
        USE operational_analytics;

        -- 3. Create the external schema mapping table
        CREATE EXTERNAL TABLE IF NOT EXISTS csv_ingested_data (
            -- Define your specific columns and matching Parquet datatypes here
            id INT,
            customer_name STRING,
            transaction_amount DOUBLE,
            product_category STRING,
            is_active BOOLEAN,
            created_at TIMESTAMP
        )
        -- Tell Athena that the underlying data layout is partitioned by date
        PARTITIONED BY (
            year INT,
            month INT,
            day INT
        )
        -- Tell Athena the files are in Parquet format
        STORED AS PARQUET
        -- Point to the ROOT folder of your processed data (do not include the specific partition strings)
        LOCATION 's3://your-processed-data-bucket/processed-data/'
        TBLPROPERTIES ('classification'='parquet');

        ```
    - Athena Partition Projection would be used to automatically sync Athena with S3 every time the Lambda function outputs a new parquet file:
        ```
        ALTER TABLE csv_ingested_data SET TBLPROPERTIES (
            'projection.enabled' = 'true',
            
            -- Define the types for your partitioned folders
            'projection.year.type' = 'integer',
            'projection.year.range' = '2024,2030', -- Adjust limits based on your data lifespan
            
            'projection.month.type' = 'integer',
            'projection.month.range' = '1,12',
            'projection.month.digits' = '2', -- Ensures it matches your 'month=06' structure
            
            'projection.day.type' = 'integer',
            'projection.day.range' = '1,31',
            'projection.day.digits' = '2',   -- Ensures it matches your 'day=17' structure
            
            -- Tell Athena exactly how to build the S3 path path dynamically
            'storage.location.template' = 's3://your-processed-data-bucket/processed-data/year=${year}/month=${month}/day=${day}/'
        );
        ```
- The `awswrangler` package used in the lambda function can be configured to automatically handle schema changes for the files uploaded to the `processed-bucket` directory. The parameters in the `wr.s3.to_parquet` function call need to be updated as follows:
    - `schema_evolution=True` updates Glue Catalog when new columns appear.
    - `catalog_versioning=True` keeps a history backup of old schemas in Glue.
- When `schema_evolution=True` is enabled, Athena resolves column differences at query execution time using specific fallback rules:
    - New Columns Added:
        - What happens: awswrangler updates the Glue Data Catalog instantly.
        - Athena Query Result: Old Parquet files that lack this column will simply return `NULL` for those rows. New files will show the actual values. No queries break.
    - Columns Dropped/Missing:
        - What happens: The column remains in the Glue Data Catalog.
        - Athena Query Result: The rows inside your newest file will return `NULL` for that specific missing column. Historical rows will still show their original data perfectly.
    - Data Type Upgrades:
        - What happens: The table updates to the wider type.
        - Athena Query Result: Athena handles this seamlessly. It reads smaller integers from old files and upcasts them into the larger format on your screen.
    - There is **one critical scenario** where schema evolution will fail and throw an error: **Data Type Incompatibility (e.g., converting a column from INT to STRING)**.
        - If a column originally held numbers and suddenly contains text strings, Athena cannot reconcile them. It will throw a `HIVE_PARTITION_SCHEMA_MISMATCH` or Parquet column type mismatch error when you run a query.
        - To mitigate this risk, enforce explicit casting inside your Lambda function before running to_parquet. If a column is prone to type shifting, proactively cast it to a string in Pandas:
            ```
            # If an ID column flips between numeric and text, force it to string early
            if 'account_id' in df.columns:
                df['account_id'] = df['account_id'].astype(str)
            ```

## Local Python Script
- Create an `upload.py` script to upload the CSV files to the appropriate folder in the S3 bucket.
    - The script can enforce a maximum file size to ensure the maximum Lambda execution time and memory limits are not exceeded. This is not strictly necessary for this project since all CSV files are less than 1GB in size.
    - Files are automatically partitioned by upload date (year/month/day).

## Streamlit (Visualization)
- The simplest way to visualize the data using Streamlit is to run queries in Athena to obtain the necessary data (queries are saved as CSV files in S3), download the files from S3, then use Pandas to convert the CSV to a data frame. This data frame can be used to create interactive tables and visualizations in Streamlit.

## Design Planning

### Summary and Objective.
- Analyze hospital healthcare data to improve patient outcomes, as well as care quality and efficiency. Key metrics that will be analyzed include nurse-to-patient ratios, total working hours, and overtime trends. 
- Raw data will be stored in CSV format in one S3 bucket, then transformed and loaded into another S3 bucket in parquet format.
- Automate Transfer of local CSV files to AWS.
- Run scheduled batch processing to transform raw CSV data into structured tables.
- Ensure data types are strictly enforced upon ingestion.

### Requirements and Commitments
- Answer the following questions:
    - What is the relationship between nurse staffing levels and hospital occupancy rates?
        - According to the processed data, there is no meaningful relationship between staffing levels and hospital occupancy rates. The data available for Q2 2024 shows a weekly pattern for nurse staffing levels, where hours worked peaked during the middle of the week, then fell during weekends. There was no meaningful trend in bed utilization rates, they remained fairly constant during the same period.
    - Which hospitals have the highest overtime hours for nurses?
        - The data provided shows cumulative total hours for all nursing employees based on employee type (lpn, rn, cna) and status (contracted vs directly employed). No data is available for hours worked by individual employees, which would be required to determine which employees worked more than 40 hours in one week or worked more hours than originally scheduled in one week.
    - What are the average staffing levels by state and hospital type?
        - Average nursing hours per patient per day during Q2 2024 were the highest Alaska, Washington D.C., and Oregon.
        - Total nursing hours worked during Q2 2024 were the highest in California, New York, and Florida.
        - Facilities with highest total nursing hours worked during Q2 2024 include Isabella Geriatric Center, Coler Rehabilitation and Nursing Care Center, and Kings Harbor Multi-Care Center.
    - What trends can you identify in patient length of stay over time?
        - Data was only available for a given facility's readmission rate, not individual patient length of stay.

### Architecture Overview
- Local Python script will push files directly to S3 using the AWS CLI or S3 presigned URL.
- Lambda function will clean and transform the data, then save it to the S3 bucket in parquet format.
- One S3 bucket will be used to store both raw and processed data.
- Athena will be used to query processed data.
- Streamlit will be used to build an interactive dashboard and gain insights.

### Data Discovery
- Daily Nurse Staffing Q2 2024 Data:
    - `PROVNUM`: Unique, 6-digit identifier for each provider.
    - `PROVNAME`: Name of healthcare facility.
    - `CITY`: City where the provider is located.
    - `STATE`: State where the provider operates.
    - `COUNTY_NAME`: County where provider is located.
    - `COUNTY_FIPS`: Federal Information Processing Standard (FIPS) code for the county.
    - `CY_QTR`: The fiscal quarter of the year (i.e. 2024Q2).
    - `WORKDATE`: The work date, in a numerical timestamp format.
    - `MDSCENSUS`: The MDS (Minimum Data Set) census, likely indicating the number of patients.
    - `HRS_RNDON`: Total hours worked by Registered Nurses (RN) on duty.
    - `HRS_RNDON_EMP`: Total hours worked by on duty RN employed directly by the provider.
    - `HRS_RNDON_CTR`: Total hours worked by on duty contracted RN.
    - `HRS_RN`: Total hours worked by all RN.
    - `HRS_RN_EMP`: Total hours worked by all directly employed RN.
    - `HRS_RN_CTR`: Total hours worked by all contracted RN.
- Skilled Nursing Facility Quality Reporting Program Provider October 2024 Data:
    - `CMS Certification Number (CCN)`: Centers for Medicare & Medicaid Services (CMS) Certification Number (CCN).
    - `Provider Name`: Name of the healthcare facility.
    - `Address Line 1`: Provider street address.
    - `City/Town`: Provider City/Town.
    - `State`: Provider State (Postal Abbreviation).
    - `ZIP Code`: Provider ZIP Code.
    - `County/Parish`: Provider county/parish name.
    - `CMS Region`: Provider CMS Region code.
    - `Measure Code`: Code consisting of the CMS ID (prefix) and the variable name (suffix) for the corresponding measure score.
    - `Score`: The measure score for the corresponding measure code.
    - `Start Date`: The start date of the reporting period for the corresponding measure code and score.
    - `End Date`: The end date of the reporting period for the corresponding measure code and score.
- Quality Measure MDS October 2024:
    - `CMS Certification Number (CCN)`: Centers for Medicare & Medicaid Services (CMS) Certification Number (CCN).
    - `Provider Name`: Name of the healthcare facility.
    - `Provider Address`: Provider street address.
    - `City/Town`: Provider City/Town.
    - `State`: Provider State (Postal Abbreviation).
    - `ZIP Code`: Provider ZIP Code.
    - `Measure Code`: Code consisting of the CMS ID (prefix) and the variable name (suffix) for the corresponding measure score.
    - `Measure Description`: The description of the measure code.
    - `Resident Type`: Whether the resident is a long-term or short-term patient.
    - `QX Measure Score`: The value of the quantity measure for quarter X (1 to 4).
    - `Four Quarter Average Score`: The value for the four-quarter average.
    - `Measure Period`: The four-quarter range covered by the measures.
- Survey Summary October 2024:
    - Lists deficiency counts for several measures for a given CCN/Provider.
        - Location
        - Processing Date
        - Count of Quality of Life and Care Deficiencies
        - Count of Resident Assessment and Care Planning Deficiencies
        - Count of Nursing and Physician Services Deficiencies
        - Count of Nutrition and Dietary Deficiencies
        - Count of Pharmacy Service Deficiencies
        - Count of Infection Control Deficiencies
        - Count of Services Deficiencies
        - Count of Laboratories Deficiencies
        - Count of Miscellaneous Deficiencies
- SNF VBP Facility Performance:
    - Lists key metrics per facility, such as readmission rates and improvement scores.
        - CMS Certification Number (CCN)
        - Provider Name
        - Provider Address
        - City/Town
        - State
        - ZIP Code
        - SNF VBP Program Ranking
        - Baseline Period: FY 2019 Risk-Standardized Readmission Rate
        - Performance Period: FY 2022 Risk-Standardized Readmission Rate
        - Achievement Score
        - Improvement Score
        - Performance Score
- Quality Measure Claims:
    - Observed vs. Expected measure scores for various measure codes for a given CCN/Provider.
        - CMS Certification Number (CCN)
        - Provider Name
        - Provider Address
        - City/Town
        - State
        - ZIP Code
        - Measure Period
        - Location
        - Processing Date
        - Measure Code
        - Resident type
        - Adjusted Score (risk-adjusted value for quality score)
        - Observed Score
        - Expected Score
- Provider Info October 2024:
    - Various provider statistics such as average residents per day.
        - CMS Certification Number (CCN)
        - Provider Name
        - Provider Address
        - City/Town
        - State
        - ZIP Code
        - Processing Date
        - Number of Certified Beds
        - Average Number of Residents per Day
        - Provider Type
        - Provider Resides in Hospital
        - Overall Rating
        - Quality Measure (QM) Rating
        - Staffing Rating
        - Reported Nurse Aide Staffing Hours per Resident per Day
        - Reported RN Staffing Hours per Resident per Day
        - Reported Licensed Staffing Hours per Resident per Day
        - Reported Total Nurse Staffing Hours per Resident per Day
        - Total nursing staff turnover
        - Registered Nurse turnover
        - Nursing Case-Mix Index
        - Case-Mix RN Staffing Hours per Resident per Day
        - Case-Mix Total Nurse Staffing Hours per Resident per Day
        - Adjusted RN Staffing Hours per Resident per Day
        - Adjusted Total Nurse Staffing Hours per Resident per Day
        - Rating Cycle X (1-3) Total Number of Health Deficiencies
        - Rating Cycle X (1-3) Health Deficiency Score
        - Rating Cycle X (1-3) Number of Health Revisits
        - Rating Cycle X (1-3) Health Revisit Score
        - Rating Cycle X (1-3) Total Health Score
        - Total Weighted Health Survey Score
        - Number of Substantiated Complaints
- Swing Bed SNF Data October 2024:
    - Measure code and score for various measure codes per CCN/Provider.
        - CMS Certification Number (CCN)
        - Provider Name
        - Provider Address
        - City/Town
        - State
        - ZIP Code
        - County
        - Measure Code
        - Score
        - Start Date
        - End Date
        - Measure Date Range
- State US Averages:
    - Staffing hours per resident per day for each state.

### Relevant Measure Codes
- National Data:
    - S_004_01_PPR_PD_NAT_UNADJUST_AVG: National unadjusted average potentially preventable readmission rate.
    - S_004_01_PPR_PD_N_BETTER_ NAT: Number of SNFs in the nation that performed better than the national rate.
    - S_004_01_PPR_PD_N_WORSE_NAT: Number of SNFs in the nation that performed worse than the national rate.
    - S_005_02_DTC_NAT_OBS_RATE: National observed discharge to community rate.
    - S_005_02_DTC_N_BETTER_NAT: Number of SNFs in the nation that performed better than the national rate.
    - S_005_02_DTC_N_WORSE_NAT: Number of SNFs in the nation that performed worse than the national rate.
- Provider Data:
    - S_004_01_PPR_PD_OBS_READM: Number of potentially preventable readmissions following discharge.
    - S_004_01_PPR_PD_VOLUME: Number of eligible stays.
    - S_004_01_PPR_PD_OBS: Unadjusted potentially preventable readmission rate.
    - S_005_02_DTC_NUMBER: Observed number of discharges to community (DTC).
    - S_005_02_DTC_VOLUME: Number of eligible stays for DTC measure.
    - S_005_02_DTC_OBS_RATE: Observed discharge to community rate.