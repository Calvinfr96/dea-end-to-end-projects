CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS order_items (
	APP_NAME VARCHAR(30),
    RESTAURANT_ID VARCHAR(30),
    CREATION_TIME_UTC TIMESTAMP,
    ORDER_ID VARCHAR(30),
    USER_ID VARCHAR(30),
    PRINTED_CARD_NUMBER VARCHAR(30),
    IS_LOYALTY BOOLEAN,
    CURRENCY VARCHAR(30),
    LINEITEM_ID VARCHAR(30),
    ITEM_CATEGORY VARCHAR(30),
    ITEM_NAME VARCHAR(30),
    ITEM_PRICE DECIMAL(10,2),
    ITEM_QUANTITY INT
);

LOAD DATA LOCAL INFILE 'restaurant_business_performance_analysis/project_resources/order_items.csv'
INTO TABLE order_items
FIELDS TERMINATED BY ',' 
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES -- Skips the header row
(
	APP_NAME,
	RESTAURANT_ID,
	CREATION_TIME_UTC,
	ORDER_ID,
	USER_ID,
	PRINTED_CARD_NUMBER,
	@var_is_loyalty,
	CURRENCY,
	LINEITEM_ID,
	ITEM_CATEGORY,
	ITEM_NAME,
	ITEM_PRICE,
	ITEM_QUANTITY
)
SET IS_LOYALTY = IF(@var_is_loyalty = 'TRUE', 1, IF(@var_is_loyalty = 'FALSE', 0, NULL));

CREATE TABLE IF NOT EXISTS order_item_options (
	ORDER_ID VARCHAR(30),
    LINEITEM_ID VARCHAR(30),
    OPTION_GROUP_NAME VARCHAR(30),
    OPTION_NAME VARCHAR(30),
    OPTION_PRICE VARCHAR(30),
    OPTION_QUANTITY INT
);

LOAD DATA LOCAL INFILE 'restaurant_business_performance_analysis/project_resources/order_item_options.csv'
INTO TABLE order_item_options
FIELDS TERMINATED BY ',' 
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES; -- Skips the header row

CREATE TABLE IF NOT EXISTS date_dim (
	DATE_KEY VARCHAR(30),
    YEAR INT,
    MONTH INT,
    WEEK INT,
    DAY_OF_WEEK VARCHAR(30),
    IS_WEEKEND BOOLEAN,
    IS_HOLIDAY BOOLEAN,
    HOLIDAY_NAME VARCHAR(30)
);

LOAD DATA LOCAL INFILE 'restaurant_business_performance_analysis/project_resources/date_dim.csv'
INTO TABLE date_dim
FIELDS TERMINATED BY ',' 
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES -- Skips the header row
(
	DATE_KEY,
    YEAR,
    MONTH,
    WEEK,
    DAY_OF_WEEK,
    @var_is_weekend,
    @var_is_holiday,
    HOLIDAY_NAME
)
SET
	IS_WEEKEND = IF(@var_is_weekend = 'TRUE', 1, IF(@var_is_weekend = 'FALSE', 0, NULL)),
    IS_HOLIDAY = IF(@var_is_holiday = 'TRUE', 1, IF(@var_is_holiday = 'FALSE', 0, NULL));