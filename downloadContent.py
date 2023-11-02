#!/usr/bin/python3

import yaml
import os
import time
import copy
import requests
import binascii
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager

from proto.toniebox.pb.freshness_check import fc_request_pb2, fc_response_pb2
from proto.toniebox.pb import taf_header_pb2

from article_yaml_helpers import YamlStruct
from tonies_json_config import Config

class HostNameIgnoringAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       assert_hostname=False)

def get_server_data(endpoint_path, data=None, method='GET', auth=None, max_length=0):
    # Paths to your PEM files
    client_cert_file = f'{Config.certs_dir}client.pem'
    private_key_file = f'{Config.certs_dir}private.pem'
    custom_ca_file = f'{Config.certs_dir}ca.pem'

    base_url = 'https://prod.de.tbs.toys'
    url = f'{base_url}/{endpoint_path}'

    headers = {}
    if auth:
        headers['Authorization'] = auth

    # Create a session and configure it for client authentication
    session = requests.Session()
    session.cert = (client_cert_file, private_key_file)
    session.verify = custom_ca_file
    session.mount('https://', HostNameIgnoringAdapter())

    # Make the request with the specified method (GET or POST)
    if method == 'GET':
        response = session.get(url, headers=headers, stream=True)
    elif method == 'POST' and data is not None:
        response = session.post(url, data=data, headers=headers, stream=True)
    else:
        print("Invalid method or missing data for POST request")
        return None

    if response.status_code == 200:
        content = b''

        if max_length:
            for chunk in response.iter_content(chunk_size=1024):
                content += chunk
                if len(content) >= max_length:
                    break

            if len(content) > max_length:
                content = content[:max_length]  # Truncate content to max_length
        else:
            content = response.content

        return content
    else:
        print(f"Request failed with status code {response.status_code}: {response.text}")
        return None

# Example usage:
# Send a GET request
endpoint_path_get = 'v1/time'
time_result = get_server_data(endpoint_path_get)

if time_result is not None:
    print("Response (GET):", time_result)

# Define the folder path containing YAML files
auth_download_dir = Config.auth_download_dir

fc_request = fc_request_pb2.TonieFreshnessCheckRequest()

yaml_infos = {}
article_infos = {}

for filename in os.listdir(auth_download_dir):
    if filename.endswith('.yaml'):
        # Read and parse the YAML file
        fileAuth = os.path.join(auth_download_dir, filename)
        with open(fileAuth, 'r') as yaml_file:
           auths = yaml.safe_load(yaml_file)
        basename = filename.replace('.yaml', '')
        taf_file = os.path.join(auth_download_dir, f'{basename}.taf')
        ogg_file = os.path.join(auth_download_dir, f'{basename}.ogg')

        if os.path.exists(taf_file) and os.path.exists(ogg_file):
            print(f"Skipping {filename}")
        else:
            for pair in auths:
                endpoint = None
                auth = None
                if "auth" in pair:
                    auth = f'BD {pair["auth"]}'
                    endpoint = f'/v2/content/{pair["ruid"]}'
                else:
                    endpoint = f'/v1/content/{pair["ruid"]}'

                print(f"Start download for {filename} with {endpoint} {auth}")
                taf = get_server_data(endpoint, method='GET', auth=auth)
                if taf is not None:
                    with open(taf_file, "wb") as file:
                        file.write(taf)
                        print(f"Saved {taf_file}")
                    with open(ogg_file, "wb") as file:
                        file.write(taf[4096:])
                        print(f"Saved {ogg_file}")

                break