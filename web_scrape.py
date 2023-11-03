#!/usr/bin/python3

import requests
import re
import json
import copy
import os
import yaml
import time
from datetime import datetime

from article_yaml_helpers import YamlStruct
from tonies_json_config import Config

# URLs of the websites
urls = [
    {"lang": "de-de", "scrap": "tonies", "url": "https://tonies.com/de-de/tonies/"},
    {"lang": "en-gb", "scrap": "tonies", "url": "https://tonies.com/en-gb/tonies/"},
    {"lang": "fr-fr", "scrap": "tonies", "url": "https://tonies.com/fr-fr/tonies/"},
    {"lang": "en-us", "scrap": "tonies-us", "url": "https://us.tonies.com/products.json?limit={limit}&page={page}"},
]

# Regular expression pattern to match JSON content
tonies_pattern = re.compile(r'type="application/json">(.*?)</script></body></html>', re.DOTALL)

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


def map_field_helper(source_path, source):
    value = source
    for path_component in source_path:
        if callable(path_component):
            value = path_component(value)
        elif isinstance(path_component, (tuple)):
            break # ignore fallback
        elif value is not None:
            if isinstance(value, list) and len(value) > 0:
                value = value[0].get(path_component, None)
            else:
                value = value.get(path_component, None)
        else:
            # Check if the next path component is a list (potential fallback)
            next_id = source_path.index(path_component) + 1
            next_path_component = None
            if next_id + 1 == len(source_path):
                next_path_component = source_path[next_id]
            if isinstance(next_path_component, (tuple)): #check if last element is a list
                value = map_field_helper(next_path_component, source)
                #print(f" Used fallback {value}, {source_path}, {path_component}, {next_path_component}")
            else:
                print(f"Problem with field mapping, not found: {source_path}, {len(source_path)}, {path_component}, {next_id}, {next_path_component}")
                return None
    return value

def map_fields(target, source, mapping):
    # Map the fields based on the mapping dictionary
    for field, source_path in mapping.items():
        if source_path[0] is None: # Fixed value
            target[field] = source_path[1]  # Assign the fixed value
        else:
            value = map_field_helper(source_path, source)
            if value is not None:
                target[field] = value

def get_active_data(yaml_base):
    return yaml_base["data"][0] # always take the first, most recent entry

def is_update_locked(article):
    yaml_base = get_yaml(article)
    if yaml_base["lock-data"]:
        print(f'Article {article} locked, skipping update.')
        return True
    return False

def extract_data_tonies(lang, article, product_data):                
    if is_update_locked(article):
        return None
    else:
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
        map_fields(yaml_data, product_data, field_mapping)

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
            return None

        match = tonies_pattern.search(html_content)
        if match:
            json_str = match.group(1)
            data = json.loads(json_str)
            try:
                yaml_data["track-desc"] = data["props"]["pageProps"]["product"]["tracks"]
            except (KeyError, TypeError):
                pass
        
        return yaml_data

def update_yaml_file(article, yaml_data):
    if yaml_data is None:
        return
    updated = False
    yaml_base = get_yaml(article)
    yaml_src_data = get_active_data(yaml_base)
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
            with open(get_yaml_path(article), "w") as yaml_file:
                print(f'Updated {article}...')
                yaml.safe_dump(yaml_base, yaml_file, default_flow_style=False, sort_keys=False, allow_unicode=True)

def get_yaml(article):
    yaml_path = get_yaml_path(article)
    if os.path.exists(yaml_path):
        with open(yaml_path, 'r') as yaml_file:
            yaml_base = yaml.safe_load(yaml_file)
    else:
        print(f"Prepare new YAML for {article}")
        yaml_base = YamlStruct.get_base()
        yaml_base["data"].append(YamlStruct.get_data())
    return yaml_base

def get_yaml_path(article):
    return f'{Config.yaml_dir}{article}.yaml'

def convert_to_unix_timestamp(iso_timestamp):
    try:
        parsed_datetime = datetime.fromisoformat(iso_timestamp)
        return int(parsed_datetime.timestamp())
    except ValueError:
        return 0  # Handle invalid timestamps gracefully

def split_title(title):
    series = None
    episode = None

    if title.endswith(" Tonie"):
        title = title[:-6]  # Remove the last 6 characters (" Tonie")

    series = title

    prefixes = ["Creative-Tonie ", "Disney & Pixar ", "Disney "]
    suffixes = [" Creative-Tonie"]
    
    for prefix in prefixes:
        if title.startswith(prefix):
            # If the title starts with one of the prefixes, set it as the series
            series = prefix.strip()
            episode = title[len(prefix):]
            break

    for suffix in suffixes:
        if title.endswith(suffix):
            # If the title ends with one of the suffixes, set it as the episode
            series = suffix.strip()
            episode = title[:-len(suffix)]
            break

    if episode is None:
        if " Creative-Tonie " in title:
            components = title.split(" Creative-Tonie ", 1)
            series = "Creative-Tonie"
            episode = components[0] + " " + components[1]
        elif ": " in title:
            components = title.split(": ", 1)
            series = components[0]
            episode = components[1]
        elif " - " in title:
            components = title.split(" - ", 1)
            series = components[0]
            episode = components[1]

             

    return (series, episode)

def extract_age_range(tags):
    age_range = None
    
    for tag in tags:
        if tag.startswith("Age Range | "):
            age_range_str = tag.replace("Age Range | ", "")
            try:
                age_range = int(age_range_str)
                break  # Exit the loop if a numeric age range is found
            except ValueError:
                continue  # Continue searching for a valid numeric age range
    
    if age_range is None:
        for tag in tags:
            if tag.startswith("Age "):
                age_range_str = tag.replace("Age ", "")
                try:
                    age_range = int(age_range_str)
                    break  # Exit the loop if a numeric age range is found
                except ValueError:
                    continue  # Continue searching for a valid numeric age range
    
    if age_range is None: # Default age range if not found in tags
        age_range = 99
    
    return age_range

def extract_data_tonies_us(lang, article, product_data):                
    if is_update_locked(article):
        return None
    else:
        yaml_data = YamlStruct.get_data()

        # Define a mapping dictionary
        field_mapping = {
                    "series": ("title", lambda x: split_title(x)[0]),
                    "episode": ("title", lambda x: split_title(x)[1]),
                    "release": ("published_at", lambda x: convert_to_unix_timestamp(x)),
                    "language": (None, lang),
                    "runtime": (None, 0),
                    "age": (None, extract_age_range(product_data["tags"])),
                    "origin": (None, "stock"),  # Fixed value
                    "category": ("product_type",),
                    "image": ("variants", "featured_image", "src", ("images", "src")), #mapper uses first entry of variants, fallback to images if not available
                    "sample": (None, None),
                    "web": (None, None),
                    "shop-id": ("id", lambda x: str(x)),
        }
        map_fields(yaml_data, product_data, field_mapping)
        
        return yaml_data

# Dictionary to store the JSON data
json_data = {}

for index, url_set in enumerate(urls):
    if url_set["scrap"] == "tonies":
        response = requests.get(url_set["url"])
        if response.status_code == 200:
            match = tonies_pattern.search(response.text)
            if match:
                json_str = match.group(1)
                # print(json_str)
                # print("")
                data = json.loads(json_str)
                json_data[index] = data
    elif url_set["scrap"] == "tonies-us":
        page = 1  # Start with page 1

        while True:
            url = url_set["url"].replace("{limit}", "250").replace("{page}", str(page))
            response = requests.get(url)
            
            if response.status_code != 200:
                print(f"Error status code {response.status_code}")
                break

            try:
                data = response.json()
            except json.JSONDecodeError:
                print(f"Error decoding json {response.text}")
                break 
            
            products = data.get("products", [])
            
            if not products:
                break  # Exit the loop if the "products" array is empty

            # Append the products to your result
            json_data[index] = json_data.get(index, []) + products
            page += 1  # Move on to the next page
        #print(json.dumps(json_data[index]))

for index, data in json_data.items():
    lang = urls[index]["lang"]
    if urls[index]["scrap"] == "tonies":
        for product in data["props"]["pageProps"]["page"]["productList"]["normalizedProducts"]:
            article = product["salesId"]
            yaml_data = extract_data_tonies(lang, article, product)
            update_yaml_file(article, yaml_data)
    if urls[index]["scrap"] == "tonies-us":
        for product in data:
            if product["product_type"] == "Tonie" or product["product_type"] == "Creative Tonie":
                if len(product["variants"]) > 0:
                    article = product["variants"][0]["sku"]
                    yaml_data = extract_data_tonies_us(lang, article, product)
                    update_yaml_file(article, yaml_data)