#!/usr/bin/python3

import os
import yaml
import json

from article_yaml_helpers import YamlStruct
from tonies_json_config import Config

yaml_dir = Config.yaml_dir
tonies_file = Config.export_tonies_file
toniesV2_file = Config.export_toniesV2_file

tonies_json = []
toniesV2_json = []

for filename in sorted(os.listdir(yaml_dir)):
    if filename.endswith('.yaml'):
        yaml_path = f"{yaml_dir}{filename}"
        with open(yaml_path, 'r') as yaml_file:
            base = yaml.safe_load(yaml_file)

        toniesV2_base = {
            "article": str(base["article"]),
            "data": []
        }
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

            toniesV2_element = {
                "series": item["series"],
                "episode": item["episode"],
                "release": item["release"],
                "language": item["language"],
                "category": item["category"],
                "runtime": item["runtime"],
                "age": item["age"],
                "origin": item["origin"],
                "picture": item["picture"],
                "sample": item["sample"],
                "web": item["web"],
                "shop-id": item["shop-id"],
                "track-desc": item["track-desc"],
                "ids": item["ids"]
            }
            toniesV2_base["data"].append(toniesV2_element)
        toniesV2_json.append(toniesV2_base)

with open(tonies_file, "w", encoding="utf-8") as json_file:
    json.dump(tonies_json, json_file, ensure_ascii=False)
    print(f"Exported {len(tonies_json)} v1 elements")

with open(toniesV2_file, "w", encoding="utf-8") as json_file:
    json.dump(toniesV2_json, json_file, ensure_ascii=False)
    print(f"Exported {len(toniesV2_json)} v2 elements")