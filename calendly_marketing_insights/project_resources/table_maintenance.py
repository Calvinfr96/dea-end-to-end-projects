# Databricks notebook source
# DBTITLE 1, Define Target Tables
TABLES_TO_MAINTAIN = [
    "workspace.default.calendly_silver",
    "workspace.default.calendly_gold_spend_analysis"
]
RETENTION_HOURS = 168  # 7 days

# COMMAND ----------
# DBTITLE 2, Execute Maintenance Loop
# 🟩 REMOVED: spark.conf.set("spark.databricks.delta.vacuum.parallelDelete.enabled", "true")
# Serverless handles this automatically!

for table in TABLES_TO_MAINTAIN:
    print(f"--- Starting Maintenance for {table} ---")
    
    # 1. Optimize Data Layout
    print(f"Optimizing file layouts and Z-Ordering...")
    if "silver" in table:
        spark.sql(f"OPTIMIZE {table} ZORDER BY (event_start_time)")
    else:
        spark.sql(f"OPTIMIZE {table} ZORDER BY (spend_date)")
        
    # 2. Clear out stale S3 historical files
    print(f"Vacuuming historical files older than {RETENTION_HOURS} hours...")
    spark.sql(f"VACUUM {table} RETAIN {RETENTION_HOURS} HOURS")
    
    print(f"Finished Maintenance for {table}\n")

print("All target Delta tables successfully optimized and cleaned!")
