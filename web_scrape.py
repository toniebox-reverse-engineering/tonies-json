#!/usr/bin/python3

import requests
import re
import json
import copy
import os
import yaml
import time
from datetime import datetime

from article_yaml_helpers import YamlStruct, YamlHelper, GeneralHelper
from tonies_json_config import Config

# URLs of the websites
urls = [
    {"lang": "de-de", "scrap": "tonies-json", "url": "https://tonies.com/de-de/tonies/"},
    {"lang": "en-gb", "scrap": "tonies-json", "url": "https://tonies.com/en-gb/tonies/"},
    {"lang": "fr-fr", "scrap": "tonies-json", "url": "https://tonies.com/fr-fr/tonies/"},
    {"lang": "de-de", "scrap": "tonies-json", "url": "https://tonies.com/de-de/clever-tonies/"},
    {"lang": "en-gb", "scrap": "tonies-json", "url": "https://tonies.com/en-gb/clever-tonies/"},
#    {"lang": "fr-fr", "scrap": "tonies-json", "url": "https://tonies.com/fr-fr/clever-tonies/"},
    {"lang": "de-de", "scrap": "tonies-json", "url": "https://tonies.com/de-de/book-tonies/"},
    {"lang": "en-gb", "scrap": "tonies-json", "url": "https://tonies.com/en-gb/book-tonies/"},
    {"lang": "en-us", "scrap": "tonies-us", "url": "https://us.tonies.com/products.json?limit={limit}&page={page}"},
    {"lang": "de-de", "scrap": "tonies-shopapi", "url": "https://api.prod.shop.tonies.com/api/os/products/?shopLocale=de-DE&offset={offset}&limit={limit}&withBucketAggs=1&categoryKey={category}"},
    {"lang": "en-gb", "scrap": "tonies-shopapi", "url": "https://api.prod.shop.tonies.com/api/os/products/?shopLocale=en-GB&offset={offset}&limit={limit}&withBucketAggs=1&categoryKey={category}"},
    {"lang": "fr-fr", "scrap": "tonies-shopapi", "url": "https://api.prod.shop.tonies.com/api/os/products/?shopLocale=fr-FR&offset={offset}&limit={limit}&withBucketAggs=1&categoryKey={category}"}, 
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
    elif lang == 'ch' or lang == 'de-ch':
        return 'de-ch'
    elif lang == 'gb' or lang == 'en-gb' or lang == 'en-int':
        return 'en-gb'
    elif lang == 'us' or lang == 'en-us':
        return 'en-us'
    elif lang == 'fr' or lang == 'fr-fr':
        return 'fr-fr'
    elif lang == 'nl' or lang == 'nl-nl':
        return 'nl-nl'
    elif lang == 'be' or lang == 'nl-be':
        return 'nl-be'
    elif lang == 'pt' or lang == 'pt-pt':
        return 'pt-pt'
    elif lang == 'es' or lang == 'es-es' or lang == 'es-lat':
        return 'es-es'
    elif lang == 'it' or lang == 'it-it':
        return 'it-it'
    elif lang == 'dk' or lang == 'da-dk':
        return 'da-dk'
    elif lang == 'fi' or lang == 'fi-fi':
        return 'fi-fi'
    elif lang == 'se' or lang == 'sv-se':
        return 'sv-se'
    elif lang == 'is' or lang == 'is-is':
        return 'is-is'
    elif lang == 'tr' or lang == 'tr-tr':
        return 'tr-tr'
    elif lang == 'pl' or lang == 'pl-pl':
        return 'pl-pl'
    elif lang == 'br' or lang == 'pt-br':
        return 'pt-br'
    else:
        print(f"Unknown language code {lang}")
        return lang


def map_field_helper(source_path, source):
    if source_path[0] == None:
        return source_path[1] # return fixed value (None, None)

    value = source
    for path_component in source_path:
        if callable(path_component):
            value = path_component(value)
        elif isinstance(path_component, (tuple)):
            break # ignore fallback
        elif value is not None:
            if isinstance(value, list):
                if len(value) > 0:
                    if (isinstance(path_component, int)):
                        if len(value) > path_component:
                            value = value[path_component]
                            continue
                    else:
                        value = value[0].get(path_component, None)
                        continue
                last_path_component = source_path[-1]
                if isinstance(last_path_component, (tuple)): #check if last element is a list
                    value = map_field_helper(last_path_component, source)
                    break
            else:
                value = value.get(path_component, None)
        else:
            last_path_component = source_path[-1]
            if isinstance(last_path_component, (tuple)): #check if last element is a list
                value = map_field_helper(last_path_component, source)
                break
                #print(f" Used fallback {value}, {source_path}, {path_component}, {next_path_component}")
            else:
                print(f"Problem with field mapping, not found: {source_path}, {len(source_path)}, {path_component}")
                return None
    return value

def map_fields(target, source, mapping):
    # Map the fields based on the mapping dictionary
    for field, source_path in mapping.items():
        if source_path[0] is None: # Fixed value
            target[field] = source_path[1]  # Assign the fixed value
        else:
            value = map_field_helper(source_path, source)
            if value is not None and ((isinstance(value, str) and value != "") or (not isinstance(value, str) and value)):
                target[field] = value

def get_active_data(yaml_base):
    return yaml_base["data"][0] # always take the first, most recent entry

article_locked={}
def is_update_locked(article):
    global article_locked
    if article not in article_locked:
        article_locked[article] = get_yaml(article, create=False)["lock-data"]

    if article_locked[article]:
        print(f'Article {article} locked, skipping update.')
        return True
    return False

def filter_data(article, yaml_data):
    if yaml_data["track-desc"] == ["Test"]:
        yaml_data["track-desc"] = []
        print(f"Skip writing Test track data of article={article}")
    return yaml_data

def extract_data_tonies(lang, article, product_data, source):                
    if is_update_locked(article):
        return
    else:
        yaml_data = YamlStruct.get_data()

        # Define a mapping dictionary
        field_mapping = {
                    "series": ("series", "label"),
                    "series-id": ("series", "key"),
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

        cache_name = f'{article}.tonies.{lang}.html'
        timeout, html_content = GeneralHelper.load_cache(cache_name, 60*60*24)

        if timeout or html_content is None: # Only update if older than 24h
            response = requests.get(yaml_data["web"])
            if response.status_code == 200:
                html_content = response.text
                GeneralHelper.save_cache(cache_name, html_content)

        cache_id = 0
        if yaml_data["language"] != lang: # skip duplicates that are in multiple shops
            cache_id = 1

        if html_content is None:
            print(f"Invalid html_content for {article}, skipping update")
            return
        
        match = tonies_pattern.search(html_content)
        if match:
            json_str = match.group(1)
            data = json.loads(json_str)
            try:
                yaml_data["track-desc"] = data["props"]["pageProps"]["product"]["tracks"]
            except (KeyError, TypeError):
                pass
        
        yaml_data = filter_data(article, yaml_data)
        merge_yaml_data(article, yaml_data, source, overwrite=True, cache_id=cache_id)
    

def extract_data_tonies_us(lang, article, product_data, source):                
    if is_update_locked(article):
        return
    else:
        yaml_data = YamlStruct.get_data()

        # Define a mapping dictionary
        field_mapping = {
                    "series": ("title", lambda x: split_title(clean_title(x))[0]),
                    "episode": ("title", lambda x: split_title(clean_title(x))[1]),
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

        cache_id = 0
        if yaml_data["language"] != lang: # skip duplicates that are in multiple shops
            cache_id = 1

        yaml_data = filter_data(article, yaml_data)
        merge_yaml_data(article, yaml_data, source, overwrite=True, cache_id=cache_id)
    
def extract_data_tonies_shopapi(lang, article, product_data, source):                
    if is_update_locked(article):
        return
    else:
        yaml_data = YamlStruct.get_data()

        # Define a mapping dictionary
        field_mapping = {
            "series": ("series", "name", (None, None)),
            "series-id": ("series", "slug", ("series", "key", (None, None))), # key or slug (slug = first scraper)
            "episode": ("name", (None, None)),
            "release": ("publicationDate", lambda x: convert_to_unix_timestamp(x)),  # Remove last 3 digits (ms to s)
            "language": ("language", "key", lambda x: lang_cleanup(x), (None, None)),  # Convert to lowercase
            "runtime": ("runTime",),
            "age": ("ageMin", lambda x: fix_age(x) if yaml_data["age"] == 99 else yaml_data["age"]),
            "origin": ("productTypeKey", lambda x: "stock" if x in ["tonie", "creative-tonie"] else x ), 
            "category": ("genre", "key", (None, None)),
            "image": ("images", 1, "url",("images", 0, "url",(None, yaml_data["image"]))), # take second image?!
            "sample": ("audioSampleUrl",),
            "web": ("productUrl", lambda x: f'https://tonies.com{x}'),
            "shop-id": ("productId",),
            "track-desc": ("tracks", lambda x: x.split("\n") if x is not None else None),
        }
        map_fields(yaml_data, product_data, field_mapping)

        if get_web_creative_tonie_category(yaml_data["web"]) is not None: #first image on creatives, missing featured image
            field_mapping = {
                "image": ("images", 0, "url",(None, yaml_data["image"])), 
           }
            map_fields(yaml_data, product_data, field_mapping)

        cache_id = 0
        #if yaml_data["language"] is None:
        #    yaml_data["language"] = previous_yaml_data["language"]
        if yaml_data["language"] != lang: # skip duplicates that are in multiple shops
            cache_id = 1
            
        yaml_data = filter_data(article, yaml_data)
        merge_yaml_data(article, yaml_data, source, overwrite=False, cache_id=cache_id)

def update_yaml_files(article, yaml_data):
    if yaml_data is None:
        return
    updated = False
    yaml_base = get_yaml(article)
    yaml_base["article"] = article
    yaml_src_data = get_active_data(yaml_base)
    for attr, data in yaml_data.items():
        if (attr == "ids"):
            continue
        if (yaml_src_data[attr] != data):
            updated = True
            yaml_src_data[attr] = data

    if updated:
        track_desc_len = len(yaml_src_data["track-desc"])
        track_len = YamlHelper.get_best_id(yaml_src_data["ids"])["tracks"]
        if track_desc_len != track_len and track_len > 0:
            print(f'Article {article} track count different ({track_desc_len}/{track_len}), warning.')
        with open(get_yaml_path(article), "w") as yaml_file:
            print(f'Updated {article}...')
            yaml.safe_dump(yaml_base, yaml_file, default_flow_style=False, sort_keys=False, allow_unicode=True)
        update_yaml_source_file(article, yaml_src_datas[0][article])

def update_yaml_source_file(article, yaml_source_data):
    if yaml_source_data is None:
        return
    updated = False
    yaml_base = get_yaml_source(article, create=False)
    yaml_base["article"] = article
    yaml_src_data = get_active_data(yaml_base)
    for attr, data in yaml_source_data.items():
        if (attr == "ids"):
            continue
        if (yaml_src_data[attr] != data):
            updated = True
            yaml_src_data[attr] = data

    if updated:
        with open(get_yaml_source_path(article), "w") as yaml_file:
            print(f'Updated source {article}...')
            yaml.safe_dump(yaml_base, yaml_file, default_flow_style=False, sort_keys=False, allow_unicode=True)


def get_yaml(article, create=True):
    yaml_path = get_yaml_path(article)
    if os.path.exists(yaml_path):
        with open(yaml_path, 'r') as yaml_file:
            yaml_base = yaml.safe_load(yaml_file)
    else:
        print(f"Prepare new YAML for {article}")
        yaml_base = YamlStruct.get_base()
        yaml_base["article"] == article
        yaml_base["data"].append(YamlStruct.get_data())
        if create:
            with open(get_yaml_path(article), "w") as yaml_file:
                yaml.safe_dump(yaml_base, yaml_file, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return yaml_base

def get_yaml_source(article, create=True):
    yaml_path = get_yaml_source_path(article)
    if os.path.exists(yaml_path):
        with open(yaml_path, 'r') as yaml_file:
            yaml_base = yaml.safe_load(yaml_file)
    else:
        yaml_base = YamlStruct.get_base()
        yaml_base["article"] == article
        yaml_base["data"].append(YamlStruct.get_data())
        if create:
            with open(get_yaml_source_path(article), "w") as yaml_file:
                yaml.safe_dump(yaml_base, yaml_file, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return yaml_base

def get_yaml_path(article):
    return f'{Config.yaml_dir}{article}.yaml'

def get_yaml_source_path(article):
    return f'{Config.yaml_source_dir}{article}.src.yaml'

def convert_to_unix_timestamp(iso_timestamp):
    if iso_timestamp is None:
        return 0
    try:
        parsed_datetime = datetime.fromisoformat(iso_timestamp)
        return int(parsed_datetime.timestamp())
    except ValueError:
        return 0  # Handle invalid timestamps gracefully

def clean_title(title):
    if title.endswith(" Tonie"):
        title = title[:-6]  # Remove the last 6 characters (" Tonie")
    if "Creativ-Tonie" in title:
        title = title.replace("Creativ-Tonie ", "Creative-Tonie")
    return title


def split_title(title):
    series = title
    episode = None

    prefixes = ["Kreativ-Tonie ", "Creative-Tonie ", "Tonie Créatif ", "Disney & Pixar ", "Disney "]
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
            components = title.split(" Creative-Tonie ", 2)
            series = "Creative-Tonie"
            episode = components[0] + " " + components[1]
        elif " Kreativ-Tonie " in title:
            components = title.split(" Kreativ-Tonie ", 2)
            series = "Kreativ-Tonie"
            episode = components[0] + " " + components[1]
        elif ": " in title:
            components = title.split(": ", 1)
            series = components[0]
            episode = components[1]
        elif " - " in title:
            components = title.split(" - ", 1)
            series = components[0]
            episode = components[1]
        elif " – " in title:
            components = title.split(" – ", 1)
            series = components[0]
            episode = components[1]
            
    if episode is not None and (episode.startswith("- " ) or episode.startswith("– ")):
        episode = episode[2:]

    return (series, episode)

def fix_age(age):
    if age is None:
        return 99
    return age
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
    
    age_range = fix_age(age_range)
    
    return age_range

# Dictionary to store the JSON data
json_data = {}

for index, url_set in enumerate(urls):
    cache_name = f'url.{index}.{url_set["scrap"]}.{url_set["lang"]}.cache'
    timeout = 60*60*24
    if not GeneralHelper.is_cache_timeout(cache_name, timeout):
        is_cached, json_data[index] = GeneralHelper.load_cache(cache_name, timeout)
        print(f'Got cache {url_set["url"]} for {url_set["lang"]}')
        continue

    print(f'Download {url_set["url"]} for {url_set["lang"]}')

    if url_set["scrap"] == "tonies-json":
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
    elif url_set["scrap"] == "tonies-shopapi":
        page = 0  # Start with page 1
        pageSize = 200

        while True:
            offset = page * pageSize
            url = url_set["url"].replace("{limit}", str(pageSize)).replace("{offset}", str(offset))
            url = url.replace("{category}", "tonies,clever-tonies,creative-tonies,tunes,book-tonies")
            response = requests.get(url)
            
            if response.status_code != 200:
                print(f"Error status code {response.status_code}")
                break

            try:
                data = response.json()
            except json.JSONDecodeError:
                print(f"Error decoding json {response.text}")
                break 
            
            documents = data.get("documents", [])
            
            if not documents:
                if page == 0:
                    print(f'First page of {url_set["url"]} is empty')
                break  # Exit the loop if the "documents" array is empty

            # Append the products to your result
            json_data[index] = json_data.get(index, []) + documents
            page += 1  # Move on to the next page
    else:
        continue
    GeneralHelper.save_cache(cache_name, json_data[index])
        #print(json.dumps(json_data[index]))

print(f'Downloads ready, extract data from dumps.')

yaml_datas = [{}, {}]
yaml_src_datas = [{}, {}]
def get_temp_yaml_data(article, cache_id):
    global yaml_datas
    if not article in yaml_datas[cache_id]:
        yaml_path = get_yaml_path(article)
        if os.path.exists(yaml_path):
            with open(yaml_path, 'r') as yaml_file:
                yaml_base = yaml.safe_load(yaml_file)
            yaml_datas[cache_id][article] = get_active_data(yaml_base)
        else:
            return YamlStruct.get_data()
    return yaml_datas[cache_id][article]
def get_temp_yaml_src_data(article, cache_id):
    global yaml_src_datas
    if not article in yaml_src_datas[cache_id]:
        return YamlStruct.get_data_source()
    return yaml_src_datas[cache_id][article]

def merge_yaml_data(article, yaml_data, source, overwrite, cache_id=0):
    global yaml_datas, yaml_src_datas
    inital_data = YamlStruct.get_data()

    if yaml_data is None:
        return
    yaml_temp_data = get_temp_yaml_data(article, cache_id)
    src_data = get_temp_yaml_src_data(article, cache_id)
    for attr, data in yaml_data.items():
        if attr == "ids":
            continue # skip id list
        if yaml_temp_data[attr] != inital_data[attr] and yaml_data[attr] == inital_data[attr]:
            continue # skip empty data overwriting existing

        if yaml_temp_data[attr] != data:
            temp_data = yaml_temp_data[attr]
            if overwrite or (not overwrite and (temp_data is None or temp_data == inital_data[attr])):
                yaml_temp_data[attr] = data
                src_data[attr] += source + ","

    yaml_datas[cache_id][article] = yaml_temp_data
    yaml_src_datas[cache_id][article] = src_data

def merge_yaml_datas(article, overwrite, src_cache_id, trg_cache_id):
    global yaml_datas, yaml_src_datas
    inital_data = YamlStruct.get_data()
    
    yaml_temp_data_src = get_temp_yaml_data(article, src_cache_id)
    src_data_src = get_temp_yaml_src_data(article, src_cache_id)
    yaml_temp_data_trg = get_temp_yaml_data(article, trg_cache_id)
    src_data_trg = get_temp_yaml_src_data(article, trg_cache_id)

    for attr, data in yaml_temp_data_src.items():
        if (attr == "ids"):
            continue
        if (yaml_temp_data_trg[attr] != data):
            temp_data = yaml_temp_data_trg[attr]
            if overwrite or (not overwrite and (temp_data is None or temp_data == inital_data[attr])):
                yaml_temp_data_trg[attr] = data
                src_data_trg[attr] += src_data_src[attr] + ","

    yaml_datas[trg_cache_id][article] = yaml_temp_data_trg
    yaml_src_datas[trg_cache_id][article] = src_data_trg

def extract_data(index, data):
    global urls
    lang = urls[index]["lang"]
    source = f'{urls[index]["scrap"]}-{lang}'
    print(f'Extract data via {lang}, {urls[index]["url"]}')
    if urls[index]["scrap"] == "tonies-json":
        for product in data["props"]["pageProps"]["page"]["productList"]["products"]:
            article = product["salesId"]
            extract_data_tonies(lang, article, product, source)
    elif urls[index]["scrap"] == "tonies-us":
        for product in data:
            if product["product_type"] == "Tonie" or product["product_type"] == "Creative Tonie":
                if len(product["variants"]) > 0:
                    article = product["variants"][0]["sku"]
                    extract_data_tonies_us(lang, article, product, source)
    elif urls[index]["scrap"] == "tonies-shopapi":
        for document in data:
            if document["productTypeKey"] in ["tonie", "creative-tonie", "tunes"]:
                article = document["salesId"]
                extract_data_tonies_shopapi(lang, article, document, source)

def get_web_creative_tonie_category(url):
    if url is None:
        return None
    if "/de-de/kreativ-tonies/" in url:
        return "Kreativ-Tonies"
    elif "/en-gb/creative-tonies/" in url:
        return "Creative-Tonies"
    elif "/fr-fr/tonies-creatifs/" in url:
        return "Tonies-Creatifs"
    return None

for index, data in json_data.items():
    extract_data(index, data)

for article, yaml_data in yaml_datas[0].items():
    merge_yaml_datas(article, overwrite=False, src_cache_id=1, trg_cache_id=0)
for article, yaml_data in yaml_datas[1].items():
    merge_yaml_datas(article, overwrite=False, src_cache_id=1, trg_cache_id=0)

print("Data extraced and updated, enhancing data now.")
for article, new_yaml_data in yaml_datas[0].items():
    title = ""
    yaml_data = copy.deepcopy(new_yaml_data)
    if yaml_data["series"] is not None:
        title += yaml_data["series"]
    if yaml_data["episode"] is not None:
        if title != "":
            title += " "
        title += yaml_data["episode"]
    merge_yaml_data(article, yaml_data, "fix-series", overwrite=True)

    category = get_web_creative_tonie_category(yaml_data["web"])
    if category is not None:
        yaml_data["category"] = category
        merge_yaml_data(article, yaml_data, "fix-creative-cat-by-web", overwrite=True)

    if yaml_data["category"] is not None:
        if yaml_data["category"] == "Kreativ-Tonies" and "Kreativ-Tonie" not in title:
            title = "Kreativ-Tonie " + title
            yaml_data["series"], yaml_data["episode"] = split_title(title)
            print(f"Fixed Kreativ-Tonie title for {article}")
            if yaml_data["language"] is None:
                yaml_data["language"] = "de-de"
        elif yaml_data["category"] == "Creative-Tonies" and "Creative-Tonie" not in title:
            title = "Creative-Tonie " + title
            yaml_data["series"], yaml_data["episode"] = split_title(title)
            print(f"Fixed Creative-Tonie title for {article}")
            if yaml_data["language"] is None:
                yaml_data["language"] = "en-gb"
        elif yaml_data["category"] == "Tonies-Creatifs" and "Tonie Créatif" not in title:
            title = "Tonie Créatif " + title
            yaml_data["series"], yaml_data["episode"] = split_title(title)
            print(f"Fixed Tonie Créatif title for {article}")
            if yaml_data["language"] is None:
                yaml_data["language"] = "fr-fr"
        merge_yaml_data(article, yaml_data, "fix-creative", overwrite=True)

        if yaml_data["category"] == "Creative Tonie" and "Creative-Tonie" in title:
            #print(f"Fixed Creative-Tonie en-us lang for {article}")
            if yaml_data["language"] is None:
                yaml_data["language"] = "en-us"
        merge_yaml_data(article, yaml_data, "fix-creative-lang", overwrite=True)


    if (yaml_data["series"] is None and yaml_data["episode"] is not None) or (yaml_data["series"] is not None and yaml_data["episode"] is None):
        yaml_data["series"], yaml_data["episode"] = split_title(title)
        merge_yaml_data(article, yaml_data, "fix-split", overwrite=True)
        
    if yaml_data["series"] is not None:
        yaml_data["series"] = yaml_data["series"].strip()
    if yaml_data["episode"] is not None:
        yaml_data["episode"] = yaml_data["episode"].strip()
    merge_yaml_data(article, yaml_data, "fix-whitespace-title", overwrite=True)

    if yaml_data["series"] is not None:
        if "Kreativ-Tonie" in yaml_data["series"]:
            if yaml_data["language"] is None:
                yaml_data["language"] = "de-de"
            yaml_data["category"] = "creative-tonie"
        elif "Creative-Tonie" in yaml_data["series"]:
            if yaml_data["language"] is None:
                yaml_data["language"] = "en-gb"
            yaml_data["category"] = "creative-tonie"
        elif "Tonie Créatif" in yaml_data["series"]:
            if yaml_data["language"] is None:
                yaml_data["language"] = "fr-fr"
            yaml_data["category"] = "creative-tonie"
        merge_yaml_data(article, yaml_data, "fix-creative-lang", overwrite=True)

    tracks = []
    for track in yaml_data["track-desc"]:
        tracks.append(track.strip())
    yaml_data["track-desc"] = tracks
    merge_yaml_data(article, yaml_data, "fix-whitespace-tracks", overwrite=True)

    update_yaml_files(article, yaml_datas[0][article])

yaml_dir = Config.yaml_dir
for filename in sorted(os.listdir(yaml_dir)):
    if filename.endswith('.yaml'):
        article = filename[:-5]
        yaml_path = f"{yaml_dir}{filename}"
        with open(yaml_path, 'r') as yaml_file:
            yaml_base = yaml.safe_load(yaml_file)

        if yaml_base["article"] != article:
            if yaml_base["article"] is None:
                yaml_base["article"] = article
                with open(get_yaml_path(article), "w") as yaml_file:
                    yaml.safe_dump(yaml_base, yaml_file, default_flow_style=False, sort_keys=False, allow_unicode=True)
                print(f"Fixed empty article in yaml for {article}")
            else:
                print(f'Filename is {filename}, but yaml-article {yaml_base["article"]} is different.')

print("webscrape done")