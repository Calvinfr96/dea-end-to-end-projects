from pyspark.sql.functions import col, to_timestamp, array_join, expr, split
from delta.tables import DeltaTable

silver_checkpoint = "s3://calendly-processed-webhook-data/_checkpoints/silver/"
silver_table_path = "s3://calendly-processed-webhook-data/tables/calendly_silver/"
target_table_name = "workspace.default.calendly_silver"

# 1. Stream from Bronze
bronze_stream = spark.readStream.table("workspace.default.calendly_bronze")

# 2. Extract and parse fields
silver_df = (bronze_stream
  .select(
    split(col("payload.uri"), "/").getItem(6).alias("invitee_id"),
    col("event").alias("webhook_event"),
    col("payload.status").alias("invitee_status"),
    col("payload.name").alias("invitee_name"),
    col("payload.email").alias("invitee_email"),
    col("payload.scheduling_method").alias("scheduling_method"),
    col("payload.timezone").alias("timezone"),
    col("payload.scheduled_event.event_type").alias("event_type"),
    to_timestamp(col("payload.scheduled_event.created_at")).alias("event_create_time"),
    to_timestamp(col("payload.scheduled_event.start_time")).alias("event_start_time"),
    to_timestamp(col("payload.scheduled_event.end_time")).alias("event_end_time"),
    col("payload.scheduled_event.name").alias("event_name"),
    array_join(expr("transform(payload.scheduled_event.event_memberships, x -> x.user_name)"), ", ").alias("host_user_names"),
    array_join(expr("transform(payload.scheduled_event.event_memberships, x -> x.user_email)"), ", ").alias("host_user_emails"),
    col("payload.scheduled_event.location.type").alias("location_type"),
    col("payload.tracking.utm_campaign").alias("utm_campaign"),
    col("payload.tracking.utm_source").alias("utm_source"),
    col("payload.tracking.utm_medium").alias("utm_medium"),
    col("ingested_at")
  )
)

# 3. Clean path-based merge logic
def merge_records_to_silver(micro_batch_df, batch_id):
    deduplicated_batch = (micro_batch_df
      .sort(col("ingested_at").desc())
      .dropDuplicates(["invitee_id"])
    )
    
    if DeltaTable.isDeltaTable(spark, silver_table_path): # Check physical files on S3 directly, ignoring memory cache bugs
        target_table = DeltaTable.forPath(spark, silver_table_path) # Load using forPath instead of forName to target files directly
        
        (target_table.alias("target")
          .merge(
            deduplicated_batch.alias("source"),
            "target.invitee_id = source.invitee_id"
          )
          .whenMatchedUpdate(set={
            "webhook_event": "source.webhook_event",
            "invitee_status": "source.invitee_status",
            "event_start_time": "source.event_start_time",
            "event_end_time": "source.event_end_time",
            "ingested_at": "source.ingested_at"
          })
          .whenNotMatchedInsertAll()
          .execute()
        )
    else:
        # Initialize table storage and catalog pointer on the first batch run
        (deduplicated_batch.write
          .format("delta")
          .mode("append")
          .option("mergeSchema", "true") # Automatically updates the schema if new aliases are found.
          .option("path", silver_table_path)
          .saveAsTable(target_table_name)
        )

# 4. Start the Stream using serverless triggers
(silver_df.writeStream
  .foreachBatch(merge_records_to_silver)
  .trigger(availableNow=True)
  .option("checkpointLocation", silver_checkpoint)
  .start()
)
