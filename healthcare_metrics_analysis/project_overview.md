# Healthcare Metrics Analysis Project

## Overview
This project will use AWS services to build a unified view of hospital staffing and operational performance across all facilities to understand how nurse availability, workload, and patient volumes affect care quality and efficiency. The system should provide clear insights into nurse-to-patient ratios, total working hours, and overtime trends by hospital and state. It should also help us track hospital occupancy, bed utilization, and identify where staffing levels are not aligned with patient load. We want to understand how staffing patterns impact outcomes such as readmissions and length of stay, and identify hospitals with high overtime or low staff-to-patient coverage. All these insights should be available through an interactive dashboard to help management improve workforce planning, optimize costs, and maintain high-quality patient care across the network.
- Source Data Extraction:
    - Download the master CSV files and 15 supporting CSV files and check them for data integrity issues (missing or corrupt files).
- Initial Data Analysis:
    - Analyze the master CSV files and supporting files to under stand the schema, relationships, and any data quality issues.
    - Identify key columns needed for joins and insights.
- Define Data Engineering Pipeline/Architecture:
    - Design a pipeline architecture for ingesting, transforming, and storing data based on the following requirements:
        - Assume you need to regularly ingest data from Google Drive.
        - Only use AWS services.
- Build Data Pipeline:
    - Build a data pipeline capable of handling raw data ingestion to a data warehouse.
- Build Dashboard:
    - Design an interactive dashboard showcasing the calculated metrics and insights. The dashboard should include:
        - Staffing insights, such as nurse-to-patient ratio.
        - Facility performance metrics, such as occupancy rates.
        - Visualizations, such as bar charts and heat maps.

- **Stramlit App URL:** https://dea-healthcare-metrics-analytics-calvinfr.streamlit.app/
- **Streamlit App Repo:** https://github.com/Calvinfr96/dea-streamlit-healthcare-metrics-analytics

## Metrics and Required Insights
- After analyzing the source data, identify 3-5 metrics that can be calculated from the list below (not all metrics listed below can be calculated with the available data):
    - Staffing Metrics:
        - Average nurse-to-patient ratio by hospital, state, and department.
            - Provider Info October 2024 Data (nursing hours per resident per day can act as a proxy).
        - Total hours worked by nurses per hospital, state, and month.
            - Daily Nurse Staffing Q2 2024 Data
        - Percentage of nurses working overtime.
        - Number of shifts per nurse (average and median) by hospital and state.
    - Facility Metrics:
        - Hospital occupancy rate trends over the past year (monthly/quarterly).
            - Distinction between Hospital occupancy rate and Bed utilization rate?
        - Bed utilization rates by hospital and department.
            - Provider Info October 2024 Data (Residents per Day / Number of Certified Beds can act as a proxy)
        - Comparison of staffing levels vs. bed occupancy rates.
            - Provider Info October 2024 Data
        - Top 10 hospitals with the highest patient throughput.
            - SNF QRP Provider Data October 2024
                - Measure Code `S_004_01_PPR_PD_OBS` (readmission rate) can act as a proxy.
        - Facilities with the lowest staffing levels compared to patient load.
            - Daily Nurse Staffing Q2 2024 Data (MDS Census vs. Total Nursing Hours)
    - Quality Metrics:
        - Patient satisfaction scores by hospital (if data is available).
        - Average length of stay (ALOS) by department and state.
        - Readmission rates within 30 days by hospital, state, and diagnosis category.
            - SNF QRP Provider Data October 2024
                - Measure Code `S_004_01_PPR_PD_OBS` (readmission rate)
        - Patient-to-nurse complaint ratio (if data is available).
        - Correlation between nurse staffing levels and readmission rates.
            - SNF QRP Provider Data October 2024
                - Measure Code `S_004_01_PPR_PD_OBS` (readmission rate)
            - State US Averages October 2024 Data (Total Nurse Staffing Hours per Resident per Day)
    - Cost Metrics:
        - Total payroll costs for nurses by hospital and state.
        - Average cost per patient stay by hospital and state.
        - Cost of overtime hours as a percentage of total payroll costs.
        - Comparison of hospital revenue vs. payroll expenses (if data is available).
    - Operational Metrics:
        - Shift utilization rates by time of day (morning, afternoon, night).
        - Peak staffing hours for each hospital and department.
            - Provider Info October 2024
        - Ratio of permanent staff to temporary/contract staff.
        - Trend analysis of nurse attrition rates (if data is available).
- Required Insights:
    - What is the relationship between nurse staffing levels and hospital occupancy rates?
        - Try to use working hours as a proxy for staffing levels.
    - Which hospitals have the highest overtime hours for nurses?
        - Can't determine overtime.
    - What are the average staffing levels by state and hospital type?
        - Average number of hours worked.
    - What trends can you identify in patient length of stay over time?
        - Can't determine length of stay.

## Data Engineering Considerations
- Data pipeline will be handling data in batches, not real-time. The data will be stored in a data warehouse, not a data lake, as we will be working with manageable amounts of structured (CSV) data, not large amounts of unstructured data.
    - Since the data is structured, an ETL process will be used to handle the data instead of ELT.
- Business requirements:
    - Analyze hospital staffing and operational metrics to make improvements that will improve patient outcomes.

## System Design Considerations
- Since data will be handled in batches instead of real-time, eventual consistency is acceptable, while strong consistency is not a strict requirement. Hospital staffing and patient data isn't updated frequently enough for data consistency to be a major issue.
- Availability and partition tolerance are important for reliably analyzing data as it is extracted from its source in batches.
- AWS S3 serves as a cost-effective storage solution for both raw and processed data.
- AWS Lambda serves as a reliable Compute/ETL tool because CSV file sizes are relatively small and can be processed in less than 15 minutes.
- AWS Athena serves a convenient way to query and analyze processed data, due its serverless architecture.

## Resources
- Requirements: https://docs.google.com/document/d/157bbXEilQNwaxbkX9mx-6FXcIv0VgO-9T9uacWAhEh4/edit?tab=t.0
- Nursing Data: https://drive.google.com/file/d/1kZMZFGfTLdcwmdhjDPZh2-XE2_gOBRCz/view?usp=sharing
- Supporting CSV Files: https://drive.google.com/drive/folders/15KqJ1MZ7JcgAkOfqcaWcALWkG0dh3jpE?usp=sharing
- Data Dictionary: https://drive.google.com/file/d/1Rvd35DqNLP8nAmjLMYclvMTtJefmg2wW/view
- Data Lake Fundamentals: https://drive.google.com/drive/folders/1Aup9vcLep0KJczAjLgxmw_Dm_IWfyag2