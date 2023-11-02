#!/usr/bin/python3

import time

class YamlStruct:
    @staticmethod
    def get_base():
        return {
            "article": None,
            "last-update": int(time.time()),
            "lock-data": False,
            "data": []
        }
    @staticmethod
    def get_data():
        return {
            "series": None,
            "episode": None,
            "release": 0,
            "language": None,
            "category": None,
            "runtime": 0,
            "age": 99,
            "origin": "stock",
            "picture": None,
            "sample": None,
            "web": None,
            "shop-id": None,
            "track-desc": [],
            "ids": []
        }
    @staticmethod
    def get_id():
        return {
            "audio-id": None,
            "hash": None,
            "size": 0,
            "tracks": 0,
        }
