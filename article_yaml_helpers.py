#!/usr/bin/python3

import time
import os
import yaml
import pickle
import json
from tonies_json_config import Config

class YamlStruct:
    @staticmethod
    def get_base():
        return {
            "article": None,
            "lock-data": False,
            "data": []
        }
    @staticmethod
    def get_data():
        return {
            "series": None,
            "series-id": None,
            "episode": None,
            "release": 0,
            "language": None,
            "category": None,
            "runtime": 0,
            "age": 99,
            "origin": None,
            "image": None,
            "sample": None,
            "web": None,
            "shop-id": None,
            "track-desc": [],
            "ids": []
        }
    @staticmethod
    def get_data_source():
        data = YamlStruct.get_data()
        for attr, entry in data.items():
            data[attr] = ""
        return data
    @staticmethod
    def get_id():
        return {
            "audio-id": 0,
            "hash": None,
            "size": 0,
            "tracks": 0,
            "confidence": 0
        }

class YamlHelper:
    @staticmethod
    def is_article_num_valid(article_num):
        return article_num is not None and not article_num.startswith("51") and not article_num.startswith("50")

    @staticmethod
    def is_meta_valuable(meta):
        if not meta:
            return False
        
        contentType = meta.get("contentType")
        tonieType = meta.get("tonieType")
        
        # Check contentType and tonieType
        is_content = (contentType == "content_tonie" and tonieType == "content")
        is_feedback = (contentType == "audio_feedback" and tonieType == "audio_feedback")
        
        return is_content or is_feedback

    @staticmethod
    def get_best_id(ids):
        id = None
        if len(ids) > 0: 
            for cur_id in ids:
                if id == None:
                    id = cur_id
                elif cur_id["confidence"] > 0:
                    id = cur_id
                    break
        if id == None:
            id = YamlStruct.get_id()
        return id
    
    @staticmethod
    def is_id_equal_without(old_id, id, ignore=()):
        if len(old_id) != len(id):
            return False
        for attr in id:
            if attr in ignore:
                continue
            if old_id[attr] != id[attr]:
                return False
        return True

class GeneralHelper:
    def is_cache_timeout(name, timeout):
        cache_path = f'{Config.cache_dir}{name}'
        file_mtime = 0
        if os.path.exists(cache_path):
            file_mtime = os.path.getmtime(cache_path)
            return (time.time() > file_mtime + timeout)
        return True
        
    def load_cache(name, timeout):
        cache_path = f'{Config.cache_dir}{name}'
        cache_data = None
        if os.path.exists(cache_path):
            file_mtime = os.path.getmtime(cache_path)   
            with open(cache_path, "rb") as cache_file:
                cache_data = pickle.load(cache_file)
        return (not GeneralHelper.is_cache_timeout(name, timeout), cache_data)
    
    def save_cache(name, data):
        cache_path = f'{Config.cache_dir}{name}'

        data_human = None
        if isinstance(data, str):
            cache_ext = "txt"
            data_human = data
        elif isinstance(data, dict):
            cache_ext = "json"
            data_human = json.dumps(data)
        elif isinstance(data, list):
            cache_ext = "json"
            data_human = json.dumps(data)

        with open(cache_path, "wb") as cache_file:
            pickle.dump(data, cache_file)

        if data_human is not None:
            cache_human_path = f'{cache_path}.{cache_ext}'
            with open(cache_human_path, "w") as cache_file:
                cache_file.write(data_human)
