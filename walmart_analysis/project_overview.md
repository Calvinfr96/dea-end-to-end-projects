# Walmart Data Analysis Project

## Overview
This project will use Snowflake, DBT, and Tableau to transform raw data into actionable intelligence, enabling data-driven decision making for Walmart's business operations. Dimension and fact tables will be built using DBT and Snowflake. These tables will be ingested by Tableau to build the required visualizations. SCD1 logic will be used to handle the `walmart_date_dim` and `walmart_store_dim` tables because no historical data needs to be saved in these tables. SCD2 logic will be used in the `walmart_sales_fact` table because historical sales data needs to be saved in this table. Each record in this table will have an insert date, as well as a version start and end date.

### Data Analysis
Data in the `departments` and `facts` tables include one entry per week per store and/or department, meaning we won't need to perform any grouping on the date column to obtain weekly sales data. The data needs to be summarized as follows once it is ingested, transformed, and modeled:
- Weekly Sales by Store and Holiday
    - Group the data in the `departments` table by `store_id` and `is_holiday`.
    - Calculate the sum of `weekly_sales`. This will give the total weekly sales across all departments in a store.
    - Since the data isn't being grouped by a specific time period (i.e. week, month), the total will represent the total weekly sales for the entire data collection.
- Weekly Sales by Temperature and Year
    - Join the `departments` and `facts` tables on `store_id` and `date`.
    - Group the data by temperature bin (10 degrees) and year (extracted from `date`).
    - Calculate the sum of `weekly_sales`. This will give total weekly sales for all departments and all stores in a given temperature range and year.
- Weekly Sales by Store Size
    - Join the `departments` and `stores` tables on `store_id`.
    - Group the data by size bin (10000 sqft).
    - Calculate the sum of `weekly_sales`. This will give the total weekly sales across all departments of all stores in a given size range.
    - Since the data isn't being grouped by a specific time period (i.e. week, month), the total will represent the total weekly sales for the entire data collection.
- Weekly Sales by Store Type and Month
    - Join the `departments` and `stores` tables on `store_id`.
    - Group the data by `type` and month (extracted from `date`).
    - Calculate the sum of `weekly_sales`. This will give the total weekly sales across all departments and all stores for a given store type and month.
- Markdown Sales by Year and Store
    - Group the data in the `facts` table by `store_id` and year (extracted from `date`).
    - Calculate the sum of markdown sales separately for `markdown_1` through `markdown_5`.
- Weekly Sales by Store Type
    - Join the `departments` and `stores` tables on `store_id`.
    - Group the data by `type`.
    - Calculate the sum of `weekly_sales`. This will give the total weekly sales across all departments and all stores for a given store type.
    - Since the data isn't being grouped by a specific time period (i.e. week, month), the total will represent the total weekly sales for the entire data collection.
- Fuel Price by Store and Year
    - Group the data in the `facts` table by `store_id` and year (extracted from `date`).
    - Calculate the mean of `fuel_price`. This will give the average cost of fuel across all stores for a given year.
- Weekly Sales by Day, Month, and Year
    - Group the data in the departments table by the day, month, and year (extracted from `date`).
    - Calculate the sum of `weekly_sales`. This will give the total weekly sales across all departments and all stores for a given day, month, or year.
    - This requires either three separate queries or three subqueries in one main query.
- Weekly Sales by CPI
    - Join the `departments` and `facts` tables on `store_id` and `date`.
    - Group the data by `cpi` (rounded to the nearest whole number).
    - Calculate the sum of `weekly_sales`. This will give the total weekly sales across all departments and all stores for a given cpi value.
    - Since the data isn't being grouped by a specific time period (i.e. week, month), the total will represent the total weekly sales for the entire data collection.
- Department-Wise Weekly Sales
    - Group the data in the `departments` table by `dept_id`.
    - Calculate the sum of `weekly_sales`. This will give the total weekly sales across all stores for a given department.
    - Since the data isn't being grouped by a specific time period (i.e. week, month), the total will represent the total weekly sales for the entire data collection.

## Resources
- Requirements: https://drive.google.com/file/d/1SOzumShXMegPpc9nfobaOrNxdqZfUvuQ/view?usp=sharing
- DBT Courses:
    - https://courses.getdbt.com/courses/fundamentals
    - https://courses.getdbt.com/courses/advanced-materializations
    - https://courses.getdbt.com/courses/jinja-macros-packages
    - https://courses.getdbt.com/courses/dbt-cloud-and-snowflake-for-developers
- DBT Git Repo: https://github.com/Calvinfr96/dea-dbt-walmart-analytics/tree/mainline
- Implementing SCD1 Using Snowflake: https://youtu.be/OA5NcEfa-mk?si=2FGSWBoZG8dfNERs
- Implementing SCD2 Using DBT: https://youtu.be/w9CEry_y53k?si=jJY7EM6gdHPubJ00
- Data Engineering Basics: https://drive.google.com/drive/folders/1jZHNgNo4whLYggsyThbs0Ix_yuppC5vW
- Connecting Snowflake With Python: https://www.snowflake.com/en/developers/guides/getting-started-with-python/#0
- Connecting Snowflake With Python (Pandas Compatible): https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-pandas