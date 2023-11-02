#!/usr/bin/python3

import requests
import re
import json
import copy

# URLs of the websites
urls = [
    "https://tonies.com/de-de/tonies/",
    "https://tonies.com/en-gb/tonies/",
    "https://tonies.com/fr-fr/tonies/"
]

# Regular expression pattern to match JSON content
pattern = re.compile(r'type="application/json">(.*?)</script></body></html>', re.DOTALL)

# Dictionary to store the JSON data
json_data = {}

for url in urls:
    response = requests.get(url)
    if response.status_code == 200:
        html_content = response.text
        match = pattern.search(html_content)
        if match:
            json_str = match.group(1)
            # print(json_str)
            # print("")
            data = json.loads(json_str)
            json_data[url] = data
# Now, json_data contains JSON data from the specified URLs
# print(json_data)

article = "10000148"

yaml_data_struct = {
    "series": None,
    "episode": None,
    "release": None,
    "language": None,
    "category": None,
    "picture": None,
    "sample": None,
    "web": None,
    "track-desc": [],
    "ids": []
}

for url, data in json_data.items():
    for product in data["props"]["pageProps"]["page"]["productList"]["normalizedProducts"]:
        if product["salesId"] == article:
            yaml_data = copy.deepcopy(yaml_data_struct)
            yaml_data["series"] = product["series"]["label"]
            yaml_data["episode"] = product["name"]
            yaml_data["release"] = product["publicationDate"] # remove 3 digits (ms instead of s)
            yaml_data["language"] = product["lcCC"] # lowercase de-de
            yaml_data["category"] = product["genre"]["key"]
            yaml_data["picture"] = product["image"]["src"] # test url
            yaml_data["sample"] = product["audioSampleUrl"] # test url
            yaml_data["web"] = f'https://tonies.com{product["path"]}' # test url

            response = requests.get(yaml_data["web"])
            if response.status_code == 200:
                html_content = response.text
                match = pattern.search(html_content)
                if match:
                    json_str = match.group(1)
                    data = json.loads(json_str)
                    yaml_data["track-desc"] = data["props"]["pageProps"]["product"]["tracks"]

            print(yaml_data)
    pass
