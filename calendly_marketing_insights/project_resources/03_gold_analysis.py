from datetime import datetime, timedelta
import io
import requests
import json
from pyspark.sql.functions import col, to_date, expr

# 1. Define Paths & Storage Parameters
gold_table_name = "workspace.default.calendly_gold_spend_analysis"
gold_storage_path = "s3://calendly-processed-webhook-data/tables/calendly_gold_spend_analysis/"

# 2. Dynamically Generate Yesterday's Date String
# Current System Year is 2026. Yesterday's format: YYYY-MM-DD
yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

# Construct the dynamic third-party URL
public_s3_url = f"https://dea-data-bucket.s3.us-east-1.amazonaws.com/calendly_spend_data/spend_data_{yesterday_str}.json"

print(f"Fetching marketing data from: {public_s3_url}")

# 3. Pull Third-Party Data Safely
try:
    response = requests.get(public_s3_url, timeout=30)
    response.raise_for_status()
    json_data = response.json()
    
    # Load into a Spark DataFrame
    spend_df = (spark.createDataFrame(json_data)
      .withColumn("spend_date", to_date(col("date"), "yyyy-MM-dd"))
      .drop("date")
    )
    
except requests.exceptions.RequestException as e:
    raise RuntimeError(f"Failed to fetch public S3 campaign data for {yesterday_str}. Error: {e}")

# 4. Create the Campaign Mapping Table
# This maps marketing channels to Calendly event type URIs
mapping_data = [
    ("facebook_paid_ads", "https://api.calendly.com/event_types/d639ecd3-8718-4068-955a-436b10d72c78"),
    ("youtube_paid_ads", "https://api.calendly.com/event_types/dbb4ec50-38cd-4bcd-bbff-efb7b5a6f098"),
    ("tiktok_paid_ads", "https://api.calendly.com/event_types/bb339e98-7a67-4af2-b584-8dbf95564312")
]
mapping_schema = ["channel_name", "calendly_event_type_uri"]
mapping_df = spark.createDataFrame(mapping_data, schema=mapping_schema)

# 5. Extract and Aggregate Silver Data (Filtered by Mapping)
silver_df = spark.read.table("workspace.default.calendly_silver")

# Filter Calendly data to include only the 3 specific campaigns, then aggregate bookings per day
calendly_daily_summary = (silver_df
  .join(mapping_df, silver_df.event_type == mapping_df.calendly_event_type_uri, "inner")
  .withColumn("meeting_date", to_date(col("event_start_time")))
  .groupBy("meeting_date", "channel_name")
  .count()
  .withColumnRenamed("count", "total_meetings_booked")
)

# 6. Filter and Prepare Spend Data
# Filter the marketing data to keep only the 3 campaigns under analysis
filtered_spend_df = spend_df.join(mapping_df, spend_df.channel == mapping_df.channel_name, "inner")

# 7. Execute the Final Analytical Join
# Join spend data with meeting volume to calculate Cost Per Acquisition (CPA) metrics
gold_analytics_df = (filtered_spend_df.join(
    calendly_daily_summary,
    (filtered_spend_df.spend_date == calendly_daily_summary.meeting_date) & 
    (filtered_spend_df.channel == calendly_daily_summary.channel_name),
    "left" # Keep spend data even if zero meetings were booked on a particular day
  )
  .select(
    col("spend_date"),
    col("channel").alias("marketing_channel"),
    col("spend").cast("double").alias("ad_spend"),
    expr("COALESCE(total_meetings_booked, 0)").alias("meetings_booked"),
    # Avoid division by zero errors if bookings equal 0
    expr("CASE WHEN total_meetings_booked > 0 THEN spend / total_meetings_booked ELSE spend END").alias("cost_per_booking")
  )
)

# 8. Overwrite the Gold Layer Presentation Table
(gold_analytics_df.write
  .format("delta")
  .mode("overwrite")
  .option("path", gold_storage_path)
  .option("overwriteSchema", "true")
  .saveAsTable(gold_table_name)
)

print("Gold presentation layer successfully updated with campaign mapping filters!")
