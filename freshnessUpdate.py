#!/usr/bin/python3

import yaml
import os
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager

from proto.toniebox.pb.freshness_check import fc_request_pb2, fc_response_pb2

class HostNameIgnoringAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       assert_hostname=False)

def ruid_to_int_uid(hex_str):
    hex_bytes = bytes.fromhex(hex_str)
    return int.from_bytes(hex_bytes, byteorder='little')

def get_server_data(endpoint_path, data=None, method='GET'):
    # Paths to your PEM files
    client_cert_file = 'work/certs/client.pem'
    private_key_file = 'work/certs/private.pem'
    custom_ca_file = 'work/certs/ca.pem'

    base_url = 'https://prod.de.tbs.toys'
    url = f'{base_url}/{endpoint_path}'

    # Create a session and configure it for client authentication
    session = requests.Session()
    session.cert = (client_cert_file, private_key_file)
    session.verify = custom_ca_file
    session.mount('https://', HostNameIgnoringAdapter())

    # Make the request with the specified method (GET or POST)
    if method == 'GET':
        response = session.get(url)
    elif method == 'POST' and data is not None:
        response = session.post(url, data=data)
    else:
        print("Invalid method or missing data for POST request")
        return None

    if response.status_code == 200:
        return response.content
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
content_yaml_folder = 'work/content/'

fc_request = fc_request_pb2.TonieFreshnessCheckRequest()

yaml_infos =  {}

for filename in os.listdir(content_yaml_folder):
    if filename.endswith('.auth.yaml'):
        yaml_info = {
            'auth' : None,
            'data' : None,
            'updated': False
        }
        # Read and parse the YAML file
        with open(os.path.join(content_yaml_folder, filename), 'r') as yaml_file:
           yaml_info["auth"] = yaml.safe_load(yaml_file)

        # Look for a corresponding .data.yaml file
        data_file_path = os.path.join(content_yaml_folder, filename.replace('.auth.yaml', '.data.yaml'))
        if os.path.exists(data_file_path):
            with open(data_file_path, 'r') as data_yaml_file:
                yaml_info["data"] = yaml.safe_load(data_yaml_file)
        else:
            yaml_info["data"] = {
                'audio-id': 0,
                'hash': '0000000000000000000000000000000000000000',
                'tracks': 0
            }


        # Create a TonieFCInfo message and populate it with data from the YAML file
        tonie_info = fc_request.tonie_infos.add()
        tonie_info.uid = ruid_to_int_uid(yaml_info["auth"]["ruid"])  # Replace with the actual YAML field name
        tonie_info.audio_id = int(yaml_info["data"]["audio-id"])
        print(f"uid: {tonie_info.uid:016x}, audio_id: {tonie_info.audio_id}")

        if tonie_info.uid in yaml_infos:
            print(f"Warning: UID {tonie_info.uid} is already in the YAML data, skipping {filename}.")
        else:
            yaml_infos[tonie_info.uid] = yaml_info

# Send a POST request with data
endpoint_path_post = 'v1/freshness-check'
fc_response_data = get_server_data(endpoint_path_post, data=fc_request.SerializeToString(), method='POST')

if fc_response_data is not None:
    print("Response (POST):", fc_response_data)
    fc_response = fc_response_pb2.TonieFreshnessCheckResponse()
    fc_response.ParseFromString(fc_response_data)
    print("Marked UIDs:")
    for marked in fc_response.tonie_marked:
        print(format(marked, '016x'))
        yaml_info = yaml_infos[marked]

        # TODO download 4k, parse taf for audio_id, hash, tracks
