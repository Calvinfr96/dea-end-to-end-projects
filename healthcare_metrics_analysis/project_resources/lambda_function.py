import awswrangler as wr # AWS Data Wrangler is a powerful library that simplifies the integration between AWS services and Pandas DataFrames. It provides high-level abstractions for reading and writing data to S3, Athena, Redshift, and more, making it easier to work with large datasets in a serverless environment like AWS Lambda.
import logging
import os
import pandas as pd
import re
import urllib.parse

from datetime import datetime

logger = logging.getLogger() # Initialize CloudWatch Logger and set logging level as INFO.
logger.setLevel(logging.INFO)

DEST_BUCKET = os.environ.get("PROCESSED_BUCKET_NAME", "your-processed-data-bucket") # Environment variable from Lambda function.
ATHENA_DB = "healthcare_data_analytics"

def clean_table_name(filename):
    """Converts a raw filename into a valid, lowercase SQL table name."""
    name_without_ext = os.path.splitext(filename)[0]
    # Replace spaces, hyphens, and dots with underscores
    clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', name_without_ext).lower()
    # SQL tables cannot start with a number
    if clean_name[0].isdigit():
        clean_name = f"table_{clean_name}"
    return clean_name

def lambda_handler(event, context):
    try:
        record = event['Records'][0]['s3'] # Record from the S3 Event Notification.
        src_bucket = record['bucket']['name']
        src_key = urllib.parse.unquote_plus(record['object']['key'], encoding='utf-8')
        
        # 1. Parse filename and generate dynamic table name
        raw_filename = os.path.basename(src_key)
        table_name = clean_table_name(raw_filename)
        logger.info(f"Targeting isolated Athena table: {table_name}")
        
        # 2. Extract incoming partition data or fallback to current execution date
        today = datetime.now()
        year, month, day = f"{today.year}", f"{today.month:02d}", f"{today.day:02d}"
        
        # 3. Establish dedicated isolated path
        dest_s3_uri = f"s3://{DEST_BUCKET}/tables/{table_name}/uploaded_year={year}/uploaded_month={month}/uploaded_day={day}/"
        source_s3_uri = f"s3://{src_bucket}/{src_key}"

        # 4. Stream data using awswrangler and perform data transformations if necessary (e.g., type casting, renaming columns)
        df = wr.s3.read_csv(path=source_s3_uri)

        logger.info(f"Applying data transformations. Total rows: {len(df)}")
        
        # Drop rows where critical ID or columns are completely empty
        if 'PROVNUM' in df.columns:
            df = df.dropna(subset=['PROVNUM'])
        if 'CMS Certification Number (CCN)' in df.columns:
            df = df.dropna(subset=['CMS Certification Number (CCN)'])
        if 'State or Nation' in df.columns:
            df = df.dropna(subset=['State or Nation'])
        
        # Clean up string columns (strip whitespace)
        string_cols = df.select_dtypes(include=['object']).columns
        df[string_cols] = df[string_cols].apply(lambda x: x.str.strip())
        
        # Enforce strict datatypes before Parquet generation
        if 'WorkDate' in df.columns:
            df['year'] = pd.to_datetime(df['WorkDate'], format='%Y%m%d', errors='coerce').dt.year.astype('Int64')  # Convert to year for partitioning
            df['month'] = pd.to_datetime(df['WorkDate'], format='%Y%m%d', errors='coerce').dt.month.astype('Int64')  # Convert to month for partitioning
            df['day'] = pd.to_datetime(df['WorkDate'], format='%Y%m%d', errors='coerce').dt.day.astype('Int64')  # Convert to day for partitioning
        if 'Processing Date' in df.columns:
            df['year'] = pd.to_datetime(df['Processing Date'], format='%Y-%m-%d', errors='coerce').dt.year.astype('Int64')
            df['month'] = pd.to_datetime(df['Processing Date'], format='%Y-%m-%d', errors='coerce').dt.month.astype('Int64')
            df['day'] = pd.to_datetime(df['Processing Date'], format='%Y-%m-%d', errors='coerce').dt.day.astype('Int64')
        if 'Start Date' in df.columns:
            df['year'] = pd.to_datetime(df['Start Date'], format='%m/%d/%Y', errors='coerce').dt.year.astype('Int64')
            df['month'] = pd.to_datetime(df['Start Date'], format='%m/%d/%Y', errors='coerce').dt.month.astype('Int64')
            df['day'] = pd.to_datetime(df['Start Date'], format='%m/%d/%Y', errors='coerce').dt.day.astype('Int64')

        # 5. Write Parquet with Schema Evolution Enabled
        logger.info(f"Writing Parquet data and managing schema evolution for: {table_name}")
        wr.s3.to_parquet(
            df=df,
            path=dest_s3_uri,
            dataset=True,
            database=ATHENA_DB,
            table=table_name,
            mode="append",                       
            partition_cols=["year", "month", "day"], 
            compression="snappy",
            index=False,
            
            # --- CRITICAL ENTRIES FOR SCHEMA EVOLUTION ---
            schema_evolution=True,   # Updates Glue Catalog when new columns appear
            catalog_versioning=True  # Keeps a history backup of old schemas in Glue
        )
        
        logger.info(f"✅ Isolated pipeline successful for table: {table_name}")
        return {'statusCode': 200, 'body': f"Registered to table {table_name}"}

    except Exception as e:
        logger.error(f"❌ Error processing isolated file: {str(e)}")
        raise e
