#!/usr/bin/env python
import snowflake.connector

# Gets the version
ctx = snowflake.connector.connect(
    user='calvinfr2', # Username
    password='iw4tZnxAtQ2E9pg', # Password
    account='TFFSMHD-PW10337' # Account identifier
    )
cs = ctx.cursor()
try:
    cs.execute("SELECT current_version()")
    one_row = cs.fetchone()
    print(one_row[0])
finally:
    cs.close()
ctx.close()