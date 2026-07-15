from pyspark.sql.functions import current_timestamp, input_file_name, col

# S3 source path configured via your AWS IAM role/instance profile
s3_raw_path = "s3://calendly-raw-webhook-data/invitee.created/"

# Good Practice: Separate folders for schema tracking and engine checkpoints
schema_location = "s3://calendly-processed-webhook-data/_metadata/schema/bronze/"
checkpoint_path = "s3://calendly-processed-webhook-data/_checkpoints/bronze/"
table_storage_path = "s3://calendly-processed-webhook-data/tables/calendly_bronze/"

# Read incoming data incrementally
# 'cloudFiles' refers to the DataBricks Auto Loader used to perform the incremental data ingestion from S3.
raw_stream = (spark.readStream
  .format("cloudFiles")
  .option("cloudFiles.format", "json")
  .option("cloudFiles.inferColumnTypes", "true")
  .option("cloudFiles.schemaLocation", schema_location) # Tells Auto Loader where to store inferred schema files.
  .load(s3_raw_path)
)

# Enrich with metadata
bronze_df = (raw_stream
  .withColumn("ingested_at", current_timestamp())
  .withColumn("source_file", col("_metadata.file_path"))
)

# Write to Bronze Delta Table
(bronze_df.writeStream
  .format("delta")
  .outputMode("append")
  .trigger(availableNow=True) 
  .option("checkpointLocation", checkpoint_path)
  .option("path", table_storage_path) # Tells Databricks to store table files in your bucket.
  .option("mergeSchema", "true") # Allows Delta to safely merge structural metadata mismatches.
  .toTable("workspace.default.calendly_bronze") 
)
