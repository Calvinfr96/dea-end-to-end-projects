USE ROLE ACCOUNTADMIN;
USE WAREHOUSE COMPUTE_WH;
USE SCHEMA WALMART_DB.PUBLIC;

-- Create Streams for DEPARTMENTS_SOURCE and STORES_SOURCE Tables
CREATE OR REPLACE STREAM WALMART_DB.PUBLIC.DEPARTMENTS_STREAM
ON TABLE WALMART_DB.PUBLIC.DEPARTMENTS_SOURCE
APPEND_ONLY = TRUE; -- Captures all inserts made to source table.

CREATE OR REPLACE STREAM WALMART_DB.PUBLIC.STORES_STREAM
ON TABLE WALMART_DB.PUBLIC.STORES_SOURCE
APPEND_ONLY = TRUE; -- Captures all inserts made to source table.

-- Test Streams
SELECT * FROM WALMART_DB.PUBLIC.DEPARTMENTS_STREAM;
SELECT * FROM WALMART_DB.PUBLIC.STORES_STREAM;

-- Create Target Tables Where Data Will Be Uploaded After Performing SCD1 Logic
CREATE OR REPLACE TABLE WALMART_DB.PUBLIC.DEPARTMENTS_TGT
(
    Store INT,
    Dept INT,
    Date DATE,
    Weekly_Sales DECIMAL(10, 2),
    IsHoliday BOOLEAN,
    INSERT_DTS TIMESTAMP(6),
    UPDATE_DTS TIMESTAMP(6)
);

CREATE OR REPLACE TABLE WALMART_DB.PUBLIC.STORES_TGT
(
    Store INT,
    Type STRING,
    Size INT,
    INSERT_DTS TIMESTAMP(6),
    UPDATE_DTS TIMESTAMP(6)
);

-- Create Stored Procedures to Capture Changes Made to Stores and Departments Data
CREATE OR REPLACE PROCEDURE WALMART_DB.PUBLIC.DEPARTMENTS_SP()
RETURNS VARCHAR(50)
LANGUAGE JAVASCRIPT
EXECUTE AS CALLER
AS
$$
try {
    //Create statement BEGIN, Begins a transaction in the current session
    snowflake.execute({sqlText:`BEGIN TRANSACTION;`});
    
    //load data from Departments Stream to a temp table
    snowflake.execute({sqlText:`
    CREATE OR REPLACE TEMPORARY TABLE WALMART_DB.PUBLIC.DEPARTMENTS_TEMP
    AS
    SELECT
        STORE,
        DEPT,
        DATE,
        WEEKLY_SALES,
        ISHOLIDAY,
        CURRENT_TIMESTAMP(6) AS INSERT_DTS,
        CURRENT_TIMESTAMP(6) AS UPDATE_DTS
    FROM WALMART_DB.PUBLIC.DEPARTMENTS_STREAM;`});
    
    //Perfom the required SCD1 logic on the Department Target table based on the primary column
    snowflake.execute({sqlText:`
    MERGE INTO WALMART_DB.PUBLIC.DEPARTMENTS_TGT TGT
    USING WALMART_DB.PUBLIC.DEPARTMENTS_TEMP TMP
    ON TGT.STORE = TMP.STORE
    AND TGT.DEPT = TMP.DEPT
    AND TGT.DATE = TMP.DATE
    
    WHEN MATCHED THEN UPDATE SET
    TGT.WEEKLY_SALES = TMP.WEEKLY_SALES,
    TGT.ISHOLIDAY = TMP.ISHOLIDAY,
    TGT.UPDATE_DTS = TMP.UPDATE_DTS
    
    WHEN NOT MATCHED THEN INSERT (
    STORE,
    DEPT,
    DATE,
    WEEKLY_SALES,
    ISHOLIDAY,
    INSERT_DTS,
    UPDATE_DTS)
    
    VALUES (
    TMP.STORE,
    TMP.DEPT,
    TMP.DATE,
    TMP.WEEKLY_SALES,
    TMP.ISHOLIDAY,
    TMP.INSERT_DTS,
    TMP.UPDATE_DTS);`});
    
    //Create statement COMMIT, Commits an open transaction in the current session
    snowflake.execute({sqlText:`COMMIT;`});
    
    //Statement returned for info and debuging purposes
    return "Store Procedure Executed Successfully";
} catch (err) {
    result = 'Error: ' + err;
    snowflake.execute({sqlText:`ROLLBACK;`});
    throw result;
}
$$;

CREATE OR REPLACE PROCEDURE WALMART_DB.PUBLIC.STORES_SP()
RETURNS VARCHAR(50)
LANGUAGE JAVASCRIPT
EXECUTE AS CALLER
AS
$$
try {
    //Create statement BEGIN, Begins a transaction in the current session
    snowflake.execute({sqlText:`BEGIN TRANSACTION;`});
    
    //load data from Stores Stream to a temp table
    snowflake.execute({sqlText:`
    CREATE OR REPLACE TEMPORARY TABLE WALMART_DB.PUBLIC.STORES_TEMP
    AS
    SELECT
        STORE,
        TYPE,
        SIZE,
        CURRENT_TIMESTAMP(6) AS INSERT_DTS,
        CURRENT_TIMESTAMP(6) AS UPDATE_DTS
    FROM WALMART_DB.PUBLIC.STORES_STREAM;`});
    
    //Perfom the required SCD1 logic on the Stores Target table based on the primary column
    snowflake.execute({sqlText:`
    MERGE INTO WALMART_DB.PUBLIC.STORES_TGT TGT
    USING WALMART_DB.PUBLIC.STORES_TEMP TMP
    ON TGT.STORE = TMP.STORE
    
    WHEN MATCHED THEN UPDATE SET
    TGT.TYPE = TMP.TYPE,
    TGT.SIZE = TMP.SIZE,
    TGT.UPDATE_DTS = TMP.UPDATE_DTS
    
    WHEN NOT MATCHED THEN INSERT (
    STORE,
    TYPE,
    SIZE,
    INSERT_DTS,
    UPDATE_DTS)
    
    VALUES (
    TMP.STORE,
    TMP.TYPE,
    TMP.SIZE,
    TMP.INSERT_DTS,
    TMP.UPDATE_DTS);`});
    
    //Create statement COMMIT, Commits an open transaction in the current session
    snowflake.execute({sqlText:`COMMIT;`});
    
    //Statement returned for info and debuging purposes
    return "Store Procedure Executed Successfully";
} catch (err) {
    result = 'Error: ' + err;
    snowflake.execute({sqlText:`ROLLBACK;`});
    throw result;
}
$$;

-- Create Tasks to Execute The Stored Procedures
CREATE OR REPLACE TASK WALMART_DB.PUBLIC.DEPARTMENTS_TASK
WAREHOUSE = COMPUTE_WH
SCHEDULE = '1 MINUTE'
WHEN SYSTEM$STREAM_HAS_DATA('WALMART_DB.PUBLIC.DEPARTMENTS_STREAM')
AS CALL WALMART_DB.PUBLIC.DEPARTMENTS_SP();

CREATE OR REPLACE TASK WALMART_DB.PUBLIC.STORES_TASK
WAREHOUSE = COMPUTE_WH
SCHEDULE = '1 MINUTE'
WHEN SYSTEM$STREAM_HAS_DATA('WALMART_DB.PUBLIC.STORES_STREAM')
AS CALL WALMART_DB.PUBLIC.STORES_SP();

-- Activate Tasks
ALTER TASK WALMART_DB.PUBLIC.DEPARTMENTS_TASK RESUME;
ALTER TASK WALMART_DB.PUBLIC.STORES_TASK RESUME;
SHOW TASKS; -- Confirm tasks have started.




-- Troubleshooting
SELECT * FROM WALMART_DB.PUBLIC.DEPARTMENTS_SOURCE; -- Data loaded successfully from S3 Storage Integration.
SELECT * FROM WALMART_DB.PUBLIC.DEPARTMENTS_TGT; -- Data not loaded successfully into target table by departments task.
SELECT * FROM WALMART_DB.PUBLIC.DEPARTMENTS_STREAM; -- Stream was not empty, meaning the departments task failed.
SELECT * FROM WALMART_DB.PUBLIC.STORES_SOURCE;
SELECT * FROM WALMART_DB.PUBLIC.STORES_TGT;
SELECT * FROM WALMART_DB.PUBLIC.STORES_STREAM; -- Stream was empty, meaning the stores task executed successfully.

EXECUTE TASK WALMART_DB.PUBLIC.DEPARTMENTS_TASK; -- Manually execute task to try and clear the stream.
SELECT SYSTEM$TASK_DEPENDENTS_ENABLE('WALMART_DB.PUBLIC.DEPARTMENTS_TASK'); -- Attempt to resume stopped tasks.

SELECT * 
FROM TABLE(information_schema.task_history())
ORDER BY scheduled_time DESC; -- Checks task history and shows any runtime errors that caused tasks to fail.

DROP TABLE WALMART_DB.PUBLIC.SNAPSHOT_FACTS_SCD2;