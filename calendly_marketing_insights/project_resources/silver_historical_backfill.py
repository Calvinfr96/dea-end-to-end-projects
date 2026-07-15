from pyspark.sql.functions import col, split
from delta.tables import DeltaTable

# 1. Define target constants
target_table_name = "workspace.default.calendly_silver"

print("Starting historical backfill for UTM and Location columns...")

# 2. Add the columns to the Silver Table Schema if they don't exist yet
spark.sql(f"""
  ALTER TABLE {target_table_name} 
  ADD COLUMNS (
    location_type STRING,
    utm_campaign STRING,
    utm_source STRING,
    utm_medium STRING
  )
""")

# 3. Read raw Bronze data as a high-speed BATCH (not a stream)
bronze_batch = spark.read.table("workspace.default.calendly_bronze")

# 4. Extract target columns and deduplicate by invitee_id
# Sorting by ingested_at ensures we grab the latest state for the backfill columns
backfill_df = (bronze_batch
  .select(
    split(col("payload.uri"), "/").getItem(6).alias("invitee_id"),
    col("payload.scheduled_event.location.type").alias("location_type"),
    col("payload.tracking.utm_campaign").alias("utm_campaign"),
    col("payload.tracking.utm_source").alias("utm_source"),
    col("payload.tracking.utm_medium").alias("utm_medium"),
    col("ingested_at")
  )
  .sort(col("ingested_at").desc())
  .dropDuplicates(["invitee_id"])
)

# 5. Connect to the existing Silver Delta Table
silver_table = DeltaTable.forName(spark, target_table_name)

# 6. Execute highly targeted MERGE to fill historical NULLs
(silver_table.alias("target")
  .merge(
    backfill_df.alias("source"),
    "target.invitee_id = source.invitee_id"
  )
  .whenMatchedUpdate(set={
    "location_type": "source.location_type",
    "utm_campaign": "source.utm_campaign",
    "utm_source": "source.utm_source",
    "utm_medium": "source.utm_medium"
  })
  .execute()
)

print("Historical backfill completed successfully! All past records updated.")
