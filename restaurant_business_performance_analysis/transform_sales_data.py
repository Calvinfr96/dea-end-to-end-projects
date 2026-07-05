import os

from pyspark.sql import functions as F
from pyspark.sql import SparkSession
from pyspark.sql import types as T
from pyspark.sql.window import Window

# Example path for macOS Homebrew installation. 
# Replace this with your actual Java installation folder path.
os.environ["JAVA_HOME"] = "/usr/local/opt/openjdk@17"

# Force Python's path to prioritize this Java version
os.environ["PATH"] = os.environ["JAVA_HOME"] + "/bin:" + os.environ["PATH"]

# Initialize your Spark Session
spark = SparkSession.builder \
    .appName("Create DataFrame From CSV") \
    .getOrCreate()

# Path to your CSV files (can be local, HDFS, S3, etc.)
order_items_file_path = "restaurant_business_performance_analysis/project_resources/order_items.csv"
order_item_options_file_path = "restaurant_business_performance_analysis/project_resources/order_item_options.csv"
date_dim_file_path = "restaurant_business_performance_analysis/project_resources/date_dim.csv"

# Load CSVs into DataFrames
order_items_df = spark.read.csv(order_items_file_path, header=True, inferSchema=True)
order_item_options_df = spark.read.csv(order_item_options_file_path, header=True, inferSchema=True)
date_dim_df = spark.read.csv(date_dim_file_path, header=True, inferSchema=True)

## Cleaning and transforming the data for analysis

# Drop rows with missing critical identifiers in order_items_df
order_items_df = order_items_df.filter(
    F.col("restaurant_id").isNotNull() & (F.trim(F.col("restaurant_id")) != "") &
    F.col("user_id").isNotNull() & (F.trim(F.col("user_id")) != "") &
    F.col("order_id").isNotNull() & (F.trim(F.col("order_id")) != "") &
    F.col("lineitem_id").isNotNull() & (F.trim(F.col("lineitem_id")) != "") &
    F.col("creation_time_utc").isNotNull()
)

# Convert creation_time_utc in order_items_df to timestamp type for proper joining
if not isinstance(order_items_df.schema["CREATION_TIME_UTC"].dataType, T.TimestampType):
    order_items_df = order_items_df.withColumn("CREATION_TIME_UTC", F.to_timestamp(F.col("CREATION_TIME_UTC")))

# Extract date from creation_time_utc to create a date_key for joining with date_dim_df
order_items_df = order_items_df.withColumn("date_key", F.to_date(F.col("CREATION_TIME_UTC")))

# Convert option_price in order_item_options_df to double type for proper aggregation
if not isinstance(order_item_options_df.schema["OPTION_PRICE"].dataType, T.DoubleType):
    order_item_options_df = order_item_options_df.withColumn("OPTION_PRICE", F.col("OPTION_PRICE").cast(T.DoubleType()))

# Convert date_key in date_dim_df to date type for proper joining
date_dim_df = date_dim_df.withColumn("date_key", F.to_date(F.col("date_key"), "dd-MM-yyyy"))

# Perform the join operations to create the sales cube
sales_fact_df = order_items_df.join(order_item_options_df, on=["order_id", "lineitem_id"], how="left") \
    .join(date_dim_df, on="date_key", how="left")

# Fill missing price and quantity values with 0 for revenue calculations
sales_fact_df = sales_fact_df.fillna(
    value = 0.0,
    subset = ["ITEM_PRICE", "ITEM_QUANTITY", "OPTION_PRICE", "OPTION_QUANTITY"]
)

# Fill missing date information for years other than 2023
sales_fact_df = sales_fact_df.withColumns({
    "year": F.coalesce(F.col("year"), F.year(F.col("CREATION_TIME_UTC"))),
    "month": F.coalesce(F.col("month"), F.month(F.col("CREATION_TIME_UTC"))),
    "week": F.coalesce(F.col("week"), F.weekofyear(F.col("CREATION_TIME_UTC"))),
    "day_of_week": F.coalesce(F.col("day_of_week"), F.date_format(F.col("CREATION_TIME_UTC"), "EEEE")),
    "is_weekend": F.coalesce(F.col("is_weekend"), F.when(F.date_format(F.col("CREATION_TIME_UTC"), "u").isin([6, 7]), True).otherwise(False)),
    "is_holiday": F.coalesce(F.col("is_holiday"), F.lit(False)),
    "holiday_name": F.coalesce(F.col("holiday_name"), F.lit(None).cast("string"))
})
sales_fact_df = sales_fact_df.withColumn("day", F.dayofmonth(F.col("CREATION_TIME_UTC")))

## Calculating Customer Lifetime Value (CLV) and other metrics

# Calculate total order revenue per user
optimized_sales_fact_df = sales_fact_df.select(
    "ORDER_ID", "USER_ID", "CREATION_TIME_UTC", "ITEM_PRICE",
    "ITEM_QUANTITY", "OPTION_PRICE", "OPTION_QUANTITY", "year",
    "month", "week", "day_of_week", "day"
)

user_revenue_df = optimized_sales_fact_df.groupBy(["ORDER_ID", "USER_ID", "CREATION_TIME_UTC"]).agg(
    F.sum(F.col("ITEM_PRICE") * F.col("ITEM_QUANTITY")).alias("base_revenue"),
    F.sum(F.col("OPTION_PRICE") * F.col("OPTION_QUANTITY")).alias("options_revenue")
)
user_revenue_df = user_revenue_df.withColumn("total_revenue", F.col("base_revenue") + F.col("options_revenue"))

# Aggregate historical revenue per user
user_clv_df = user_revenue_df.groupBy("USER_ID").agg(
    F.sum("total_revenue").alias("historical_user_revenue"),
    F.countDistinct("ORDER_ID").alias("total_user_orders"),
    F.min("CREATION_TIME_UTC").alias("first_order_date"),
    F.max("CREATION_TIME_UTC").alias("last_order_date")
)
user_clv_df = user_clv_df.withColumn("avg_user_order_value", F.col("historical_user_revenue") / F.col("total_user_orders"))

# Calculate global metrics for the entire dataset
global_metrics_df = user_clv_df.agg(
    F.avg("total_user_orders").alias("avg_orders_per_user"),
    F.avg("avg_user_order_value").alias("avg_order_value_per_user"),
    F.avg(F.date_diff(F.col("last_order_date"), F.col("first_order_date"))).alias("avg_customer_lifespan_days")
)

# Calculate the Customer Lifetime Value (CLV) for each user
global_user_metrics = user_clv_df.crossJoin(global_metrics_df)
global_user_metrics = global_user_metrics.withColumn(
    "customer_lifetime_value",
    F.col("avg_user_order_value") * F.col("total_user_orders") * F.col("avg_customer_lifespan_days")
)

# Categorize users based on their CLV into segments
clv_window = Window.orderBy(F.col("customer_lifetime_value"))
global_user_metrics = global_user_metrics.withColumn("clv_segment", F.ntile(5).over(clv_window))
global_user_metrics = global_user_metrics.withColumn(
    "clv_segment_label",
    F.when(F.col("clv_segment") == 1, "Low Value")
    .when(F.col("clv_segment") == 5, "High Value")
    .otherwise("Medium Value")
).drop("clv_segment") ## Join with sales_fact_df to get the final optimized DataFrame with all metrics

## Calculate Recency, Frequency, and Monetary (RFM) metrics for each user

# Find the most recent order date amongst all users to calculate recency
most_recent_order_date = optimized_sales_fact_df.agg(F.max("CREATION_TIME_UTC")).collect()[0][0]

# Calculate days since last order for each user
rfm_metrics_df = optimized_sales_fact_df.groupBy("USER_ID").agg(
    F.datediff(F.lit(most_recent_order_date), F.max("CREATION_TIME_UTC")).alias("days_since_last_order")
)

# Calculate a user's monthly order frequency
monthly_user_order_stats_df = optimized_sales_fact_df.groupBy("USER_ID", "year", "month").agg(
    F.count("ORDER_ID").alias("monthly_order_count"),
    F.sum(F.col("ITEM_PRICE") * F.col("ITEM_QUANTITY") + F.col("OPTION_PRICE") * F.col("OPTION_QUANTITY")).alias("monthly_revenue")
)
rfm_metrics_df = monthly_user_order_stats_df.join(rfm_metrics_df, on="USER_ID", how="left")

# Add RFM score based on recency, frequency, and monetary value
r_window = Window.orderBy(F.col("days_since_last_order").desc()) # Order by descending to give more recent customers (lower days since last order) a higher score
f_window = Window.orderBy(F.col("monthly_order_count"))
m_window = Window.orderBy(F.col("monthly_revenue"))

rfm_metrics_df = rfm_metrics_df.withColumn(
    "recency_score_segment", F.ntile(2).over(r_window)
)
rfm_metrics_df = rfm_metrics_df.withColumn(
    "monthly_recency_score",
     F.when(F.col("recency_score_segment") == 1, "Low").otherwise("High")
).drop("recency_score_segment")

rfm_metrics_df = rfm_metrics_df.withColumn(
    "frequency_score_segment", F.ntile(2).over(f_window)
)
rfm_metrics_df = rfm_metrics_df.withColumn(
    "monthly_frequency_score",
    F.when(F.col("frequency_score_segment") == 1, "Low").otherwise("High")
).drop("frequency_score_segment")

rfm_metrics_df = rfm_metrics_df.withColumn(
    "monetary_score_segment", F.ntile(2).over(m_window)
)
rfm_metrics_df = rfm_metrics_df.withColumn(
    "monthly_monetary_score",
    F.when(F.col("monetary_score_segment") == 1, "Low").otherwise("High")
).drop("monetary_score_segment")

# Add labels determining if a customer is a VIP, new customer, or churned based on RFM scores
rfm_metrics_df = rfm_metrics_df.withColumn(
    "Monthly_VIP_Status",
    F.when((F.col("monthly_recency_score") == "High") & (F.col("monthly_frequency_score") == "High") & (F.col("monthly_monetary_score") == "High"), True)
    .otherwise(False)
)
rfm_metrics_df = rfm_metrics_df.withColumn(
    "Monthly_New_Customer_Status",
    F.when((F.col("monthly_recency_score") == "High") & (F.col("monthly_frequency_score") == "Low") & (F.col("monthly_monetary_score") == "Low"), True)
    .otherwise(False)
)
rfm_metrics_df = rfm_metrics_df.withColumn(
    "Monthly_Churn_Risk_Status",
    F.when((F.col("monthly_recency_score") == "Low") & (F.col("monthly_frequency_score") == "Low") & (F.col("monthly_monetary_score") == "Low"), True)
    .otherwise(False) ## Join with sales_fact_df to get the final optimized DataFrame with all metrics
)

sales_fact_df_final = sales_fact_df.join(global_user_metrics, on="USER_ID", how="inner") \
    .join(rfm_metrics_df, on=["USER_ID", "year", "month"], how="inner")

"""
Copy and paste this code into your AWS Glue job script. This script is designed to transform sales data for a restaurant business performance analysis project. It performs data cleaning, transformation, and calculates various metrics such as Customer Lifetime Value (CLV) and Recency, Frequency, and Monetary (RFM) scores.
Make sure to adjust the file paths and any other configurations as needed for your specific environment.

import sys

from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame
from awsglue.job import Job
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql import types as T
from pyspark.sql.window import Window

# Initialize Glue and Spark contexts
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
spark.conf.set("spark.sql.legacy.timeParserPolicy", "LEGACY")
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Read data from RDS MySQL tables using AWS Glue connection
order_items_df = glueContext.create_dynamic_frame.from_options(
    connection_type="mysql",
    connection_options={
        "useConnectionProperties": "true",
        "connectionName": "rds-glue-connection", # Name of the AWS Glue connection to your RDS MySQL database
        "dbtable": "raw.order_items"
    }
).toDF()

order_item_options_df = glueContext.create_dynamic_frame.from_options(
    connection_type="mysql",
    connection_options={
        "useConnectionProperties": "true",
        "connectionName": "rds-glue-connection", # Name of the AWS Glue connection to your RDS MySQL database
        "dbtable": "raw.order_item_options"
    }
).toDF()

date_dim_df = glueContext.create_dynamic_frame.from_options(
    connection_type="mysql",
    connection_options={
        "useConnectionProperties": "true",
        "connectionName": "rds-glue-connection", # Name of the AWS Glue connection to your RDS MySQL database
        "dbtable": "raw.date_dim"
    }
).toDF()

## Cleaning and transforming the data for analysis

# Drop rows with missing critical identifiers in order_items_df
order_items_df = order_items_df.filter(
    F.col("restaurant_id").isNotNull() & (F.trim(F.col("restaurant_id")) != "") &
    F.col("user_id").isNotNull() & (F.trim(F.col("user_id")) != "") &
    F.col("order_id").isNotNull() & (F.trim(F.col("order_id")) != "") &
    F.col("lineitem_id").isNotNull() & (F.trim(F.col("lineitem_id")) != "") &
    F.col("creation_time_utc").isNotNull()
)

# Convert creation_time_utc in order_items_df to timestamp type for proper joining
if not isinstance(order_items_df.schema["CREATION_TIME_UTC"].dataType, T.TimestampType):
    order_items_df = order_items_df.withColumn("CREATION_TIME_UTC", F.to_timestamp(F.col("CREATION_TIME_UTC")))

# Extract date from creation_time_utc to create a date_key for joining with date_dim_df
order_items_df = order_items_df.withColumn("date_key", F.to_date(F.col("CREATION_TIME_UTC")))

# Convert option_price in order_item_options_df to double type for proper aggregation
if not isinstance(order_item_options_df.schema["OPTION_PRICE"].dataType, T.DoubleType):
    order_item_options_df = order_item_options_df.withColumn("OPTION_PRICE", F.col("OPTION_PRICE").cast(T.DoubleType()))

# Convert date_key in date_dim_df to date type for proper joining
date_dim_df = date_dim_df.withColumn("date_key", F.to_date(F.col("date_key"), "dd-MM-yyyy"))

# Perform the join operations to create the sales cube
sales_fact_df = order_items_df.join(order_item_options_df, on=["order_id", "lineitem_id"], how="left") \
    .join(date_dim_df, on="date_key", how="left")

# Fill missing price and quantity values with 0 for revenue calculations
sales_fact_df = sales_fact_df.fillna(
    value = 0.0,
    subset = ["ITEM_PRICE", "ITEM_QUANTITY", "OPTION_PRICE", "OPTION_QUANTITY"]
)

# Fill missing date information for years other than 2023
sales_fact_df = sales_fact_df.withColumns({
    "year": F.coalesce(F.col("year"), F.year(F.col("CREATION_TIME_UTC"))),
    "month": F.coalesce(F.col("month"), F.month(F.col("CREATION_TIME_UTC"))),
    "week": F.coalesce(F.col("week"), F.weekofyear(F.col("CREATION_TIME_UTC"))),
    "day_of_week": F.coalesce(F.col("day_of_week"), F.date_format(F.col("CREATION_TIME_UTC"), "EEEE")),
    "is_weekend": F.coalesce(F.col("is_weekend"), F.when(F.date_format(F.col("CREATION_TIME_UTC"), "u").isin([6, 7]), True).otherwise(False)),
    "is_holiday": F.coalesce(F.col("is_holiday"), F.lit(False)),
    "holiday_name": F.coalesce(F.col("holiday_name"), F.lit(None).cast("string"))
})
sales_fact_df = sales_fact_df.withColumn("day", F.dayofmonth(F.col("CREATION_TIME_UTC")))

## Calculating Customer Lifetime Value (CLV) and other metrics

# Calculate total order revenue per user
optimized_sales_fact_df = sales_fact_df.select(
    "ORDER_ID", "USER_ID", "CREATION_TIME_UTC", "ITEM_PRICE",
    "ITEM_QUANTITY", "OPTION_PRICE", "OPTION_QUANTITY", "year",
    "month", "week", "day_of_week", "day"
)

user_revenue_df = optimized_sales_fact_df.groupBy(["ORDER_ID", "USER_ID", "CREATION_TIME_UTC"]).agg(
    F.sum(F.col("ITEM_PRICE") * F.col("ITEM_QUANTITY")).alias("base_revenue"),
    F.sum(F.col("OPTION_PRICE") * F.col("OPTION_QUANTITY")).alias("options_revenue")
)
user_revenue_df = user_revenue_df.withColumn("total_revenue", F.col("base_revenue") + F.col("options_revenue"))

# Aggregate historical revenue per user
user_clv_df = user_revenue_df.groupBy("USER_ID").agg(
    F.sum("total_revenue").alias("historical_user_revenue"),
    F.countDistinct("ORDER_ID").alias("total_user_orders"),
    F.min("CREATION_TIME_UTC").alias("first_order_date"),
    F.max("CREATION_TIME_UTC").alias("last_order_date")
)
user_clv_df = user_clv_df.withColumn("avg_user_order_value", F.col("historical_user_revenue") / F.col("total_user_orders"))

# Calculate global metrics for the entire dataset
global_metrics_df = user_clv_df.agg(
    F.avg("total_user_orders").alias("avg_orders_per_user"),
    F.avg("avg_user_order_value").alias("avg_order_value_per_user"),
    F.avg(F.date_diff(F.col("last_order_date"), F.col("first_order_date"))).alias("avg_customer_lifespan_days")
)

# Calculate the Customer Lifetime Value (CLV) for each user
global_user_metrics = user_clv_df.crossJoin(global_metrics_df)
global_user_metrics = global_user_metrics.withColumn(
    "customer_lifetime_value",
    F.col("avg_user_order_value") * F.col("total_user_orders") * F.col("avg_customer_lifespan_days")
)

# Categorize users based on their CLV into segments
clv_window = Window.orderBy(F.col("customer_lifetime_value"))
global_user_metrics = global_user_metrics.withColumn("clv_segment", F.ntile(5).over(clv_window))
global_user_metrics = global_user_metrics.withColumn(
    "clv_segment_label",
    F.when(F.col("clv_segment") == 1, "Low Value")
    .when(F.col("clv_segment") == 5, "High Value")
    .otherwise("Medium Value")
).drop("clv_segment") ## Join with sales_fact_df to get the final optimized DataFrame with all metrics

## Calculate Recency, Frequency, and Monetary (RFM) metrics for each user

# Find the most recent order date amongst all users to calculate recency
most_recent_order_date = optimized_sales_fact_df.agg(F.max("CREATION_TIME_UTC")).collect()[0][0]

# Calculate days since last order for each user
rfm_metrics_df = optimized_sales_fact_df.groupBy("USER_ID").agg(
    F.datediff(F.lit(most_recent_order_date), F.max("CREATION_TIME_UTC")).alias("days_since_last_order")
)

# Calculate a user's monthly order frequency
monthly_user_order_stats_df = optimized_sales_fact_df.groupBy("USER_ID", "year", "month").agg(
    F.count("ORDER_ID").alias("monthly_order_count"),
    F.sum(F.col("ITEM_PRICE") * F.col("ITEM_QUANTITY") + F.col("OPTION_PRICE") * F.col("OPTION_QUANTITY")).alias("monthly_revenue")
)
rfm_metrics_df = monthly_user_order_stats_df.join(rfm_metrics_df, on="USER_ID", how="left")

# Add RFM score based on recency, frequency, and monetary value
r_window = Window.orderBy(F.col("days_since_last_order").desc()) # Order by descending to give more recent customers (lower days since last order) a higher score
f_window = Window.orderBy(F.col("monthly_order_count"))
m_window = Window.orderBy(F.col("monthly_revenue"))

rfm_metrics_df = rfm_metrics_df.withColumn(
    "recency_score_segment", F.ntile(2).over(r_window)
)
rfm_metrics_df = rfm_metrics_df.withColumn(
    "monthly_recency_score",
    F.when(F.col("recency_score_segment") == 1, "Low").otherwise("High")
).drop("recency_score_segment")

rfm_metrics_df = rfm_metrics_df.withColumn(
    "frequency_score_segment", F.ntile(2).over(f_window)
)
rfm_metrics_df = rfm_metrics_df.withColumn(
    "monthly_frequency_score",
    F.when(F.col("frequency_score_segment") == 1, "Low").otherwise("High")
).drop("frequency_score_segment")

rfm_metrics_df = rfm_metrics_df.withColumn(
    "monetary_score_segment", F.ntile(2).over(m_window)
)
rfm_metrics_df = rfm_metrics_df.withColumn(
    "monthly_monetary_score",
    F.when(F.col("monetary_score_segment") == 1, "Low").otherwise("High")
).drop("monetary_score_segment")

# Add labels determining if a customer is a VIP, new customer, or churned based on RFM scores
rfm_metrics_df = rfm_metrics_df.withColumn(
    "Monthly_VIP_Status",
    F.when((F.col("monthly_recency_score") == "High") & (F.col("monthly_frequency_score") == "High") & (F.col("monthly_monetary_score") == "High"), True)
    .otherwise(False)
)
rfm_metrics_df = rfm_metrics_df.withColumn(
    "Monthly_New_Customer_Status",
    F.when((F.col("monthly_recency_score") == "High") & (F.col("monthly_frequency_score") == "Low") & (F.col("monthly_monetary_score") == "Low"), True)
    .otherwise(False)
)
rfm_metrics_df = rfm_metrics_df.withColumn(
    "Monthly_Churn_Risk_Status",
    F.when((F.col("monthly_recency_score") == "Low") & (F.col("monthly_frequency_score") == "Low") & (F.col("monthly_monetary_score") == "Low"), True)
    .otherwise(False) ## Join with sales_fact_df to get the final optimized DataFrame with all metrics
)

sales_fact_df_final = sales_fact_df.join(global_user_metrics, on="USER_ID", how="inner") \
    .join(rfm_metrics_df, on=["USER_ID", "year", "month"], how="inner")

# Create a DynamicFrame from the final DataFrame to return to AWS Glue
result_dyn_frame = DynamicFrame.fromDF(sales_fact_df_final, glueContext, "sales_fact_df_final")

glueContext.write_dynamic_frame.from_options(
    frame=result_dyn_frame,
    connection_type="s3",
    format="parquet",
    connection_options={
        "path": "s3://restaurant-analysis-calvinfr/gold/sales_performance/", # Path to your S3 bucket where the transformed data will be stored
        "compression": "snappy"
    }
)

job.commit()
"""
