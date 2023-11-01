#!/usr/bin/python3

import copy
import os
import requests

import json
import yaml

yaml_dir = "work/yaml"
tonies_json_file = "./work/tonies.json"

if not os.path.exists(yaml_dir):
    os.makedirs(yaml_dir)

# Check if the JSON file exists
if not os.path.isfile(tonies_json_file):
    url = "https://gt-blog.de/JSON/tonies.json"

    # Send an HTTP GET request to the URL
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Open the local file for writing and save the content of the response
        with open(tonies_json_file, 'wb') as file:
            file.write(response.content)
        print(f"File '{tonies_json_file}' has been downloaded successfully.")
    else:
        print(f"Failed to download the file. Status code: {response.status_code}")


[os.remove(os.path.join(yaml_dir, filename)) for filename in os.listdir(yaml_dir) if os.path.isfile(os.path.join(yaml_dir, filename))]

yaml_base_struct = {
    "article": None,
    "data": []
}
yaml_data_struct = {
    "series": None,
    "episode": None,
    "release": None,
    "language": None,
    "category": None,
    "picture": None,
    "tracks": [],
    "ids": []
}
yaml_ids_struct = {
    "audio-id": None,
    "hash": None
}

# Load JSON data from a file
with open("./work/tonies.json", "r") as json_file:
    data = json.load(json_file)

# Sort the data by the "model" key
data = sorted(data, key=lambda x: x['model'])

# Create a dictionary to organize the data by article
article_data = {}

for item in data:
    article = item['model']
    if article not in article_data:
        article_data[article] = []
    article_data[article].append(item)

# Convert and save each article's data to a separate YAML file
for article, article_items in article_data.items():
    yaml_file_path = f"{yaml_dir}/{article}.yaml"

    yaml_dict = copy.deepcopy(yaml_base_struct)
    yaml_dict["article"] = article
    for item in article_items:
        yaml_data = copy.deepcopy(yaml_data_struct)
        yaml_data["series"] = item["series"]
        yaml_data["episode"] = item["episodes"]
        if item["release"] != '':
            yaml_data["release"] = int(item["release"])
        yaml_data["language"] = item["language"].lower()
        yaml_data["category"] = item["category"]
        yaml_data["picture"] = item["pic"]

        for track in item["tracks"]:
            yaml_data["tracks"].append(track)

        for audio_id, hash_value in zip(item["audio_id"], item["hash"]):
            yaml_ids = copy.deepcopy(yaml_ids_struct)
            yaml_ids["audio-id"] = int(audio_id)
            yaml_ids["hash"] = hash_value
            yaml_data["ids"].append(yaml_ids)

        if yaml_data["language"] == 'de':
            yaml_data["language"] = 'de-de'
        elif yaml_data["language"] == 'gb':
            yaml_data["language"] = 'en-gb'
        elif yaml_data["language"] == 'us':
            yaml_data["language"] = 'en-us'

        # Check if language is one of the specified codes
        if yaml_data["language"] not in ["de-de", "en-gb", "en-us", "fr-fr"]:
            # Print the 'language' value
            print(f"Wrong language for article: {article}, Language: {yaml_data['language']}")

        yaml_dict["data"].append(yaml_data)
        
    if len(yaml_dict["data"]) > 1:
         print(f"article: {article}, with more than one entry")
        

    with open(yaml_file_path, "w") as yaml_file:
        yaml.dump(yaml_dict, yaml_file, default_flow_style=False, sort_keys=False, allow_unicode=True)
