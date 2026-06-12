# Walmart Data Analysis Project Summary

## Snowflake
- Snowflake will be used as the data warehouse in this project, storing and managing data securely and efficiently. Snowflake provides elasticity and performance that enables handling of large, growing data sets such as those used by companies like Walmart.
- Project Setup:
    - Create a `WALMART_DB` database to store the raw data.
    - Create a `S3_INT` storage integration to connect with S3, specifying the `s3://walmart-analysis-calvinfr/data/` URI as the `STORAGE_ALLOWED_LOCATIONS`.
    - Create a `MY_CSV_FORMAT` file format to parse the CSV data stored in S3.
    - Create three external stages, one for each CSV file. Three different stages are needed because each CSV file has a different schema.
        - For each external stage specify the URI as `s3://walmart-analysis-calvinfr/data/{folder}/`, where `folder` is the folder where the CSV file is stored.
        - Three different folders are created in the `data` folder of the S3 bucket so that the same `S3_INT` storage integration can be used with each of the three stages.
    - Create three different tables, one for each CSV file.
    - Create three different snowpipes, copying data from each of three stages into each of three respective tables.
- Implementing SCD1 Logic for Department and Store Data:
    - The SCD1 logic will be built using a combination of streams, tasks, and stored procedures.
    - The stream tracks data changes in the source table, while the task executes the SCD1 logic using a stored procedure and uploads the data to a target table.
    - Create two streams, one for the departments data and the other for the stores data. These streams will be used to track changes in the `DEPARTMENTS_SOURCE` and `STORES_SOURCE` tables.
    - Create `DEPARTMENTS_TGT` and `STORES_TGT` target tables that will be used by the tasks implementing the SCD1 logic.
    - Create two stored procedures which merge data from the two previously created streams into the respective target tables using SCD1 logic.
    - For each of the two previously created stored procedures, create a task which automatically executes the stored procedure on a regular basis (defined by the `SCHEDULE` variable, default is `1 MINUTE`). After the tasks are created, activate them.
- Implementing SCD2 logic for Fact Data:
    - The logic will mostly reside in a DBT macro. However, the initial setup must be done in Snowflake.
    - Use the same storage integration and file format used to pull departments and stores data from S3 to create an external stage for the facts data.
- Creating Summary Tables Using Python:
    - Connect Snowflake with Python using the pandas-compatible connector. This will allow you to create summary tables for data analysis using Pandas data frames.
    - Create a summary table for each of the required reports listed in the project overview.
    - Upload the tables to the `WALKMART_DB` database under a new `ANALYTICS` schema.

### Connecting Snowflake With Python
- Once all of the base tables (`DEPARTMENTS_TGT`, `STORES_TGT`, and `SNAPSHOT_FACTS_SCD2`) have been created using Snowflake and DBT, the summary tables can be created using pandas data frames in a Python script.
- Install the necessary packages in a virtual environment in the root directory for the git repo:
    ```
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    pip install 'snowflake-connector-python[pandas]'
    ```
- Test the connection by creating a python script in a `validate.py` file:
    ```
    #!/usr/bin/env python
    import snowflake.connector

    # Gets the version
    ctx = snowflake.connector.connect(
        user='<your_user_name>',
        password='<your_password>',
        account='<your_account_name>'
        )
    cs = ctx.cursor()
    try:
        cs.execute("SELECT current_version()")
        one_row = cs.fetchone()
        print(one_row[0])
    finally:
        cs.close()
    ctx.close()
    ```

### S3/Snowflake Troubleshooting
- S3 is used as a data lake to store the CSV files containing the Walmart data
- Snowflake and DBT are used to transform and model the raw data to prepare it for analysis.
- Snowflake integrates with S3 using a storage integration:
    - The `STORAGE_AWS_IAM_USER_ARN` and `STORAGE_AWS_EXTERNAL_ID` properties from the storage integration are used to establish a connection with the S3 bucket. `STORAGE_ALLOWED_LOCATIONS` are the S3 location(s) that the storage integration is allowed to access.
- The storage integration is used to build an external stage that draws data from a particular S3 location. This location is typically the same as `STORAGE_ALLOWED_LOCATIONS`, but doesn't need to be.
- We could try to create three separate stages for the three different CSV files, placing them in separate folders.

## Data Build Tool (DBT)
- DBT will be used to transform and model the data. DBT acts as a modern data engineering workflow that promotes collaboration, version control, and data lineage tracking. With dbt, data models can be accurately built, tested, and deployed, ensuring data accuracy and consistency throughout the analysis process.
- Create a [repository](https://github.com/Calvinfr96/dea-dbt-walmart-analytics/tree/mainline) in GitHub to keep track of changes made to the project in the DBT UI.
- Create a `/staging/public/` directory in the `models` folder of the project. This will be used to store the staging models for the project.
- In the `/staging/public/` directory, create a `src_public.yml` file to declare the sources that will be used to create the staging models. Then, create three staging models, one for each table in the `WALMART_DB` database.
- Update the `dbt_project.yml` file to set the default materialization to view for models in the `staging` directory.
- Implementing SCD2 Logic for Fact Data:
    - Create a macro that performs the following tasks:
        - Creates a transient table if one doesn't exist.
        - Deletes all data from the table.
        - Copies data from the external stage into the table, effectively performing a full table refresh on the transient table.
        - Transient table is used because it's more cost efficient than a permanent table (time travel for a transient table is capped at one day).
        - The variables used in the macro must be configured in the `dbt_project.yml` file after the `models` configuration.
    - Create a staging table that queries all data from the transient table (created/updated by the macro) and renames the columns appropriately.
    - Create a snapshot. The DBT snapshot is the tool that performs the SCD2 logic based on the `target_database`, `target_schema`, and `unique_key`. Executing the snapshot creates a table in Snowflake with the records from the facts table.
        - Three different columns keep track of record history:
            - `dbt_updated_at`: The timestamp showing exactly when dbt inserted this record.
            - `dbt_valid_from`: The timestamp marking when this row version became active, typically the same as `dbt_updated_at`.
            - `dbt_valid_to`: The timestamp marking when this row version became obsolete. This value is set to `NULL` for newly added records, denoting them as currently active. When a record is updated, this value is populated with the time the update occurred. Subsequently, a new record with the updated value(s) is added, with `dbt_valid_to` set to `NULL`.
        - In the case of the facts data, store and date need to be used as a composite primary key for the `unique_key` setting of the snapshot config. This composite key can be created in the `select` statement following the snapshot config block.
        - `dbt.concat` is used with a `-` delimiter to ensure the concatenation produces a unique key (The pairs (1, 12) and (11 2) produce the same key when concatenated without a '-').
        - When the `dbt snapshot` command is run in the DBT UI, it saves the snapshot in the database and schema used to establish the connection with Snowflake.

### Snowflake/DBT Troubleshooting
- When creating a connection between Snowflake and DBT, we need to pick a role, warehouse, and database that will be used to form the connection.
- DBT models will determine how the raw data is shaped. Models are SQL statements used to shape data. Each model represents a modular step of logic between raw and transformed data. Each model typically maps to a table or a view in Snowflake. Staging models typically have a one-to-one relationship with the raw data sources.

## Tableau
- Tableau will be used visualize and explore the data after it has been transformed and modeled. Tableau is a powerful business intelligence and data visualization platform that provides an intuitive interface and interactive dashboards, empowering Walmart's teams to interact with the data and gain actionable insights effortlessly.
- Create a connector to link Tableau with Snowflake:
    - Use `{org_name}-{account_name}.snowflakecomputing.com` as the server.
    - Choose the appropriate role and warehouse.
    - Choose to authenticate using username and password.
- Once the connection is established, select the schema containing the summary tables.
- When Tableau imports data from a table it splits the columns into two different categories:
    - Dimensions are columns with descriptive values, such as genre or name.
    - Measures are columns with numerical values, such as sales and rank.
- Each visualization in Tableau requires a minimum number of dimensions and/or measures. For example, a scatter plot requires 0 or more dimensions and 2 to 4 measures.
- Each dimension or measure can be added to a visualization as a column (x-axis) or a row (y-axis).
- Dimensions can also be added as a mark. For example, if you plot global sales per year as a line graph, adding genre as a mark will create a separate line for each genre in the graph, showing global sales for each genre and year.
- The marks section of the Tableau UI contains useful visualization tools such as color and label. A dimension can be added to this section multiple times to assign a color and label to the dimension in the graph.
- Dimensions can also be added as a filter, allowing the graph to be quickly filtered based on that dimension. For example, adding platform as a filter allows the graph to be modified such that it only aggregates global sales for the selected platforms.
- Each visualization is created in a separate sheet. These sheets can be added to a dashboard to build a wholistic view of multiple metrics.

### Tableau Troubleshooting
- Connection issues with snowflake were experienced when trying to add more than one independent table to the same data source. Tableau does not support this.
    - Tableau's default logical layer ("Relationships") expects a clean primary/foreign key link between tables. This is cannot be accomplished by adding more than one independent, final table to the same data source.
- Solution:
    - Choose 'Extract' for the data source's connection type. This allows Tableau to take a snapshot of your data and save it locally on your Mac. Data sources extracted from snowflake using this connection type can be updated by right-clicking the data source and refreshing it.
    - Save the extracted to your Tableau repository when you open a new worksheet.
    - For each new worksheet, create a new data source and independently add (using the 'Extract' connection type) the single table needed for visualization. Save each data file to your Tableau repository.
- Visualizing Weekly Sales by Temperature and Year:
    - Select the bar as the mark type.
    - Add temperature range and year as columns.
    - Add total weekly sales as a row, changing it from a measure to a dimension.
    - Manually sort the temperature range as needed.

## AWS S3
- Create an S3 bucket to store the Walmart store/sales data.
- Create a `data` folder and manually upload the CSV files to that folder.

## AWS IAM
- Create am IAM role that will grant Snowflake access to the S3 bucket, allowing the storage integration to transfer data from S3 to the compute warehouse.