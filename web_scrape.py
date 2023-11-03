#!/usr/bin/python3

import requests
import re
import json
import copy
import os
import yaml
import time

from article_yaml_helpers import YamlStruct
from tonies_json_config import Config

# URLs of the websites
urls = [
    {"lang": "de-de", "url": "https://tonies.com/de-de/tonies/"},
    {"lang": "en-gb", "url": "https://tonies.com/en-gb/tonies/"},
    {"lang": "fr-fr", "url": "https://tonies.com/fr-fr/tonies/"},
]

# Regular expression pattern to match JSON content
pattern = re.compile(r'type="application/json">(.*?)</script></body></html>', re.DOTALL)

# Dictionary to store the JSON data
json_data = {}

for url_set in urls:
    response = requests.get(url_set["url"])
    if response.status_code == 200:
        html_content = response.text
        match = pattern.search(html_content)
        if match:
            json_str = match.group(1)
            # print(json_str)
            # print("")
            data = json.loads(json_str)
            json_data[url_set["lang"]] = data
# Now, json_data contains JSON data from the specified URLs
# print(json_data)

def convert_to_int(value):
    try:
        return int(str(value)[:-3])
    except (ValueError, TypeError):
        if value is not None:
            print(f"Invalid value for timestamp {value}")
        return 0
    
def lang_cleanup(value):
    lang = value.lower()
    if lang == 'de' or lang == 'de-de':
        return 'de-de'
    elif lang == 'gb' or lang == 'en-gb':
        return 'en-gb'
    elif lang == 'us' or lang == 'en-us':
        return 'en-us'
    elif lang == 'fr' or lang == 'fr-fr':
        return 'fr-fr'
    else:
        print(f"Unknown language code {lang}")
        return lang


    
for lang, data in json_data.items():
    for product in data["props"]["pageProps"]["page"]["productList"]["normalizedProducts"]:
        article = product["salesId"]
        yaml_path = f'{Config.yaml_dir}{article}.yaml'
        if os.path.exists(yaml_path):
            with open(yaml_path, 'r') as yaml_file:
                yaml_base = yaml.safe_load(yaml_file)
        else:
            print(f"Prepare new YAML for {article}")
            yaml_base = YamlStruct.get_base()
            yaml_base["data"].append(YamlStruct.get_data())
             
        if yaml_base["lock-data"]:
            print(f'Article {article} locked, skipping update.')
        else:
            yaml_src_data = yaml_base["data"][0] # always take the first, most recent entry
            yaml_data = YamlStruct.get_data()

            # Define a mapping dictionary
            field_mapping = {
                "series": ("series", "label"),
                "episode": ("name",),
                "release": ("publicationDate", lambda x: convert_to_int(x)),  # Remove last 3 digits (ms to s)
                "language": ("lcCC", lambda x: lang_cleanup(x)),  # Convert to lowercase
                "runtime": ("runTime",),
                "age": ("ageMin",),
                "origin": (None, "stock"),  # Fixed value
                "category": ("genre", "key"),
                "image": ("image", "src"),
                "sample": ("audioSampleUrl",),
                "web": ("path", lambda x: f'https://tonies.com{x}'),
                "shop-id": ("id",),
            }

            # Map the fields based on the mapping dictionary
            for field, source_path in field_mapping.items():
                if source_path[0] is None: # Fixed value
                    yaml_data[field] = source_path[1]  # Assign the fixed value
                else:
                    value = product
                    for path_component in source_path:
                        if callable(path_component):
                            value = path_component(value)
                        else:
                            value = value.get(path_component, None)

                    if value is not None:
                        yaml_data[field] = value

            cache_path = f'{Config.cache_dir}{article}.tonies.{lang}.html'
            file_mtime = 0
            if os.path.exists(cache_path):
                file_mtime = os.path.getmtime(cache_path)

            if time.time() > file_mtime + 60*60*24: # Only update if older than 24h
                response = requests.get(yaml_data["web"])
                if response.status_code == 200:
                    html_content = response.text
                    with open(cache_path, "w") as cache_file:
                        cache_file.write(html_content)
            else:
                with open(cache_path, "r") as cache_file:
                    html_content = cache_file.read()

            if yaml_data["language"] != lang: # skip duplicates that are in multiple shops
                continue

            match = pattern.search(html_content)
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
                try:
                    yaml_data["track-desc"] = data["props"]["pageProps"]["product"]["tracks"]
                except (KeyError, TypeError):
                    pass
            
            updated = False
            for attr, data in yaml_data.items():
                if (attr == "ids"):
                    continue
                if (yaml_src_data[attr] != data):
                    updated = True
                    yaml_src_data[attr] = data

            if updated:
                track_desc_len = len(yaml_src_data["track-desc"])
                track_len = 0
                if len(yaml_src_data["ids"]) > 0:
                    track_len = yaml_src_data["ids"][0]["tracks"]
                if track_desc_len != track_len and track_len > 0:
                    print(f'Article {article} track count different ({track_desc_len}/{track_len}), skipping.')
                else:
                    yaml_base["last-update"] = int(time.time())
                    with open(yaml_path, "w") as yaml_file:
                        print(f'Updated {article}...')
                        yaml.safe_dump(yaml_base, yaml_file, default_flow_style=False, sort_keys=False, allow_unicode=True)
