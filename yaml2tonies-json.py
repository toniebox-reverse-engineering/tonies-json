#!/usr/bin/python3

import os
import yaml
import json

from article_yaml_helpers import YamlStruct
from tonies_json_config import Config

yaml_dir = Config.yaml_dir
tonies_file = Config.export_tonies_file

tonies_json = []
toniesV2_json = []

for filename in sorted(os.listdir(yaml_dir)):
    if filename.endswith('.yaml'):
        yaml_path = f"{yaml_dir}{filename}"
        with open(yaml_path, 'r') as yaml_file:
            base = yaml.safe_load(yaml_file)

        for item in base["data"]:
            audio_ids = []
            hashes = []
            for id in item["ids"]:
                audio_ids.append(str(id["audio-id"]))
                hashes.append(id["hash"])
            tonies_element = {
                "model": str(base["article"]),
                "audio_id": audio_ids,
                "hash": hashes,
                "title": f'{item["series"]} - {item["episode"]}',
                "series": item["series"],
                "episodes": item["episode"],
                "tracks": item["track-desc"],
                "release": str(item["release"]),
                "language": item["language"],
                "category": item["category"],
                "pic": item["picture"]
            }
            tonies_json.append(tonies_element)

with open(tonies_file, "w") as json_file:
    json.dump(tonies_json, json_file)
    print(f"Exported {len(tonies_json)} elements")