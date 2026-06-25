#!/usr/bin/python3

class Config:
    # Base paths needed for the configuration below
    tonies_json_repo = "../tonies-json/"
    tonies_json_release_repo = "../tonies-json-release/"
    work_dir = "./work/"
    
    # ---------------------------------------------------------
    # Required for scripts in tonies-json (web_scrape.py, yaml2tonies-json.py)
    # ---------------------------------------------------------
    yaml_dir = f"{tonies_json_repo}yaml/"
    yaml_source_dir = f"{tonies_json_repo}source-yaml/"
    cache_dir = f"{work_dir}cache/"
    export_tonies_file = f"{tonies_json_release_repo}tonies.json"
    export_toniesV2_file = f"{tonies_json_release_repo}toniesV2.json"
