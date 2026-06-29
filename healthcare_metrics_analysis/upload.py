import os
import boto3
from botocore.exceptions import ClientError
from datetime import datetime

# --- Configuration ---
BUCKET_NAME = "healthcare-data-analysis-calvinfr"
AWS_PROFILE = "default"  # Uses credentials from your ~/.aws/credentials file
MAX_FILE_SIZE_MB = 250

# --- Initialize Boto3 ---
# Setting a profile keeps your access keys out of your code files
session = boto3.Session(profile_name=AWS_PROFILE)
s3_client = session.client('s3')

def upload_csv_to_s3(file_path):
    # 1. Validate file existence
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found at {file_path}")
        return False

    # 2. Enforce the 250MB Architectural Limit
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        print(f"❌ Aborting: {os.path.basename(file_path)} is {file_size_mb:.1f}MB.")
        print(f"   Exceeds design limit of {MAX_FILE_SIZE_MB}MB.")
        return False

    # 3. Generate a dynamic S3 Hive-style path (YYYY/MM/DD)
    file_name = os.path.basename(file_path)
    today = datetime.now()
    s3_key = f"raw-csvs/year={today.year}/month={today.month:02d}/day={today.day:02d}/{file_name}"

    print(f"⏳ Uploading {file_name} ({file_size_mb:.1f}MB) to s3://{BUCKET_NAME}/{s3_key}...")

    # 4. Upload with metadata and error handling
    try:
        s3_client.upload_file(
            Filename=file_path,
            Bucket=BUCKET_NAME,
            Key=s3_key,
            ExtraArgs={
                'ContentType': 'text/csv',
                'Metadata': {'uploaded_by': 'local_ingestion_script'}
            }
        )
        print("✅ Upload successful!")
        return True
    except ClientError as e:
        print(f"❌ AWS Client Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False

if __name__ == "__main__":
    # Example usage
    target_file = "/Users/Apple/Downloads/healthcare_analysis_project/target_data/quality_measure_mds_oct_2024.csv"  # Update this path to your local CSV file
    upload_csv_to_s3(target_file)
