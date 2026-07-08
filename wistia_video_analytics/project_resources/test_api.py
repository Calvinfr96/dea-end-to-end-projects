import os
import json
import boto3
import urllib3

http = urllib3.PoolManager()
wistia_token = "0323ade64e13f79821bdc0f2a9410d9ec3873aa9df01f8a4a54d4e0f3dd2e6b4"
headers = urllib3.make_headers(basic_auth=f"api:{wistia_token}")
show_media_stats_wistia_base_url = "https://api.wistia.com/modern/stats/medias"
list_visitors_wistia_base_url = "https://api.wistia.com/modern/stats/visitors"
media_id = "8hunphufxp"

api_response = http.request('GET', f"{show_media_stats_wistia_base_url}/{media_id}", headers=headers)

if api_response.status != 200:
    raise Exception(f"Wistia API returned HTTP status {api_response.status}")

# Parse response to validate structure
raw_json_data = json.loads(api_response.data.decode('utf-8'))

print(f"Response Type: {type(api_response)}")