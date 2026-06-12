import pandas as pd
from snowflake.connector import connect
from snowflake.connector.pandas_tools import write_pandas

# Create a connection to Snowflake
conn = connect(
    user='calvinfr2', # Username
    password='iw4tZnxAtQ2E9pg', # Password
    account='TFFSMHD-PW10337' # Account identifier
    )

# Setup the role, warehouse, database, and schema
conn.cursor().execute("USE ROLE ACCOUNTADMIN")
conn.cursor().execute("USE WAREHOUSE COMPUTE_WH")
conn.cursor().execute("USE DATABASE WALMART_DB")
conn.cursor().execute("CREATE SCHEMA IF NOT EXISTS ANALYTICS")
conn.cursor().execute("USE SCHEMA ANALYTICS")

## Test the connection by running a simple query
try:
    with conn.cursor() as cs:
        cs.execute("SELECT current_version()")
        one_row = cs.fetchone()
except Exception as e:
    print(f"An error occurred: {e}")

# Retrieve stores, departments, and facts data and save them as a dataframe
departments_df = None
stores_df = None
facts_df = None

try:
    with conn.cursor() as cs:
        cs.execute("SELECT * FROM WALMART_DB.DBT_CFRANCIS.STG_PUBLIC__DEPARTMENTS_TGT")
        departments_df = cs.fetch_pandas_all()

        cs.execute("SELECT * FROM WALMART_DB.DBT_CFRANCIS.STG_PUBLIC__STORES_TGT")
        stores_df = cs.fetch_pandas_all()

        cs.execute("SELECT * FROM WALMART_DB.PUBLIC.SNAPSHOT_FACTS_SCD2")
        facts_df = cs.fetch_pandas_all()
except Exception as e:
    print(f"An error occurred while fetching data: {e}")

# Merge the departments and facts dataframes on the store_id and date columns
departments_facts_df = pd.merge(departments_df, facts_df, on=['STORE_ID', 'DATE'], how='inner')

# Merge the departments and stores dataframes on the store_id column
departments_stores_df = pd.merge(departments_df, stores_df, on='STORE_ID', how='inner')

# Weekly Sales by Store and Holiday
weekly_sales_store_holiday_df = departments_df.groupby(['STORE_ID', 'IS_HOLIDAY']).agg(TOTAL_WEEKLY_SALES=('WEEKLY_SALES', 'sum')).reset_index()

success, nchunks, nrows, _ = write_pandas(
    conn=conn,
    df=weekly_sales_store_holiday_df,
    table_name='WEEKLY_SALES_STORE_HOLIDAY',
    auto_create_table=True
)

print(f"Success: {success}, Rows written: {nrows}")

# Weekly Sales by Temperature and Year
departments_facts_df_copy = departments_facts_df.copy()

departments_facts_df_copy['YEAR'] = pd.to_datetime(departments_facts_df_copy['DATE']).dt.year
departments_facts_df_copy['BIN_LOWER'] = (round(departments_facts_df_copy['TEMPERATURE']) // 10) * 10
departments_facts_df_copy['TEMP_RANGE'] = departments_facts_df_copy['BIN_LOWER'].astype(str) + ' to ' + (departments_facts_df_copy['BIN_LOWER'] + 9).astype(str)

weekly_sales_temp_year_df = departments_facts_df_copy.groupby(['TEMP_RANGE', 'YEAR']).agg(TOTAL_WEEKLY_SALES=('WEEKLY_SALES', 'sum')).reset_index()

success, nchunks, nrows, _ = write_pandas(
    conn=conn,
    df=weekly_sales_temp_year_df,
    table_name='WEEKLY_SALES_TEMP_YEAR',
    auto_create_table=True
)

print(f"Success: {success}, Rows written: {nrows}")

# Weekly Sales by Store Size
departments_stores_df_copy = departments_stores_df.copy()

departments_stores_df_copy['BIN_LOWER'] = (round(departments_stores_df_copy['SIZE']) // 10000) * 10000
departments_stores_df_copy['STORE_SIZE_RANGE'] = departments_stores_df_copy['BIN_LOWER'].astype(str) + ' to ' + (departments_stores_df_copy['BIN_LOWER'] + 9999).astype(str)

weekly_sales_store_size_df = departments_stores_df_copy.groupby(['STORE_SIZE_RANGE']).agg(TOTAL_WEEKLY_SALES=('WEEKLY_SALES', 'sum')).reset_index()

success, nchunks, nrows, _ = write_pandas(
    conn=conn,
    df=weekly_sales_store_size_df,
    table_name='WEEKLY_SALES_STORE_SIZE',
    auto_create_table=True
)

print(f"Success: {success}, Rows written: {nrows}")

# Weekly Sales by Store Type and Month
departments_stores_df_copy = departments_stores_df.copy()

departments_stores_df_copy['MONTH'] = pd.to_datetime(departments_stores_df_copy['DATE']).dt.month_name()

weekly_sales_store_type_month_df = departments_stores_df_copy.groupby(['TYPE', 'MONTH']).agg(TOTAL_WEEKLY_SALES=('WEEKLY_SALES', 'sum')).reset_index()

success, nchunks, nrows, _ = write_pandas(
    conn=conn,
    df=weekly_sales_store_type_month_df,
    table_name='WEEKLY_SALES_STORE_TYPE_MONTH',
    auto_create_table=True
)

print(f"Success: {success}, Rows written: {nrows}")

# Markdown Sales by Year and Store
facts_df_copy_cleaned = facts_df.copy().dropna(subset=['MARKDOWN_1', 'MARKDOWN_2', 'MARKDOWN_3', 'MARKDOWN_4', 'MARKDOWN_5'], how='all')
facts_df_copy_cleaned.fillna({'MARKDOWN_1': 0, 'MARKDOWN_2': 0, 'MARKDOWN_3': 0, 'MARKDOWN_4': 0, 'MARKDOWN_5': 0}, inplace=True)

facts_df_copy_cleaned['YEAR'] = pd.to_datetime(facts_df_copy_cleaned['DATE']).dt.year

markdown_sales_year_store_df = facts_df_copy_cleaned.groupby(['YEAR', 'STORE_ID']).agg(
    MARKDOWN_1_TOTAL_SALES=('MARKDOWN_1', 'sum'),
    MARKDOWN_2_TOTAL_SALES=('MARKDOWN_2', 'sum'),
    MARKDOWN_3_TOTAL_SALES=('MARKDOWN_3', 'sum'),
    MARKDOWN_4_TOTAL_SALES=('MARKDOWN_4', 'sum'),
    MARKDOWN_5_TOTAL_SALES=('MARKDOWN_5', 'sum')
    ).reset_index()

success, nchunks, nrows, _ = write_pandas(
    conn=conn,
    df=markdown_sales_year_store_df,
    table_name='MARKDOWN_SALES_YEAR_STORE',
    auto_create_table=True
)

print(f"Success: {success}, Rows written: {nrows}")

# Weekly Sales by Store Type
weekly_sales_store_type_df = departments_stores_df.groupby(['TYPE']).agg(TOTAL_WEEKLY_SALES=('WEEKLY_SALES', 'sum')).reset_index()

success, nchunks, nrows, _ = write_pandas(
    conn=conn,
    df=weekly_sales_store_type_df,
    table_name='WEEKLY_SALES_STORE_TYPE',
    auto_create_table=True
)

print(f"Success: {success}, Rows written: {nrows}")

# Average Fuel Price by Store and Year
facts_df_copy = facts_df.copy()

facts_df_copy['YEAR'] = pd.to_datetime(facts_df_copy['DATE']).dt.year

fuel_price_store_year_df = facts_df_copy.groupby(['STORE_ID', 'YEAR']).agg(AVERAGE_FUEL_COST=('FUEL_PRICE', 'mean')).reset_index()

success, nchunks, nrows, _ = write_pandas(
    conn=conn,
    df=fuel_price_store_year_df,
    table_name='FUEL_PRICE_STORE_YEAR',
    auto_create_table=True
)

print(f"Success: {success}, Rows written: {nrows}")

# Weekly Sales by Day, Month, and Year
departments_df_copy = departments_df.copy()

departments_df_copy['DAY'] = pd.to_datetime(departments_df_copy['DATE']).dt.day
departments_df_copy['MONTH'] = pd.to_datetime(departments_df_copy['DATE']).dt.month_name()
departments_df_copy['YEAR'] = pd.to_datetime(departments_df_copy['DATE']).dt.year

weekly_sales_by_day = departments_df_copy.groupby(['DAY']).agg(WEEKLY_SALES_BY_DAY = ('WEEKLY_SALES', 'sum')).reset_index()
weekly_sales_by_month = departments_df_copy.groupby(['MONTH']).agg(WEEKLY_SALES_BY_MONTH = ('WEEKLY_SALES', 'sum')).reset_index()
weekly_sales_by_year = departments_df_copy.groupby(['YEAR']).agg(WEEKLY_SALES_BY_YEAR = ('WEEKLY_SALES', 'sum')).reset_index()

success, nchunks, nrows, _ = write_pandas(
    conn=conn,
    df=weekly_sales_by_day,
    table_name='WEEKLY_SALES_BY_DAY',
    auto_create_table=True
)

print(f"Success: {success}, Rows written: {nrows}")

success, nchunks, nrows, _ = write_pandas(
    conn=conn,
    df=weekly_sales_by_month,
    table_name='WEEKLY_SALES_BY_MONTH',
    auto_create_table=True
)

print(f"Success: {success}, Rows written: {nrows}")

success, nchunks, nrows, _ = write_pandas(
    conn=conn,
    df=weekly_sales_by_year,
    table_name='WEEKLY_SALES_BY_YEAR',
    auto_create_table=True
)

print(f"Success: {success}, Rows written: {nrows}")

# Weekly Sales by CPI
departments_facts_df_copy = departments_facts_df.copy()

departments_facts_df_copy['BIN_LOWER'] = (round(departments_facts_df_copy['CPI']) // 10) * 10
departments_facts_df_copy['CPI_RANGE'] = departments_facts_df_copy['BIN_LOWER'].astype(str) + ' to ' + (departments_facts_df_copy['BIN_LOWER'] + 9).astype(str)

weekly_sales_by_cpi_df = departments_facts_df_copy.groupby(['CPI_RANGE']).agg(TOTAL_WEEKLY_SALES=('WEEKLY_SALES', 'sum')).reset_index()

success, nchunks, nrows, _ = write_pandas(
    conn=conn,
    df=weekly_sales_by_cpi_df,
    table_name='WEEKLY_SALES_BY_CPI',
    auto_create_table=True
)

print(f"Success: {success}, Rows written: {nrows}")

# Department-Wise Weekly Sales
department_weekly_sales_df = departments_df.groupby(['DEPT_ID']).agg(TOTAL_WEEKLY_SALES=('WEEKLY_SALES', 'sum')).reset_index()

success, nchunks, nrows, _ = write_pandas(
    conn=conn,
    df=department_weekly_sales_df,
    table_name='DEPARTMENT_WEEKLY_SALES',
    auto_create_table=True
)

print(f"Success: {success}, Rows written: {nrows}")

# Close Snowflake Connection
conn.close()