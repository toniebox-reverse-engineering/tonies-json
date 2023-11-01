#!/usr/bin/python3

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
        return response.text
    else:
        print(f"Request failed with status code {response.status_code}: {response.text}")
        return None

# Example usage:
# Send a GET request
endpoint_path_get = 'v1/time'
time_result = get_server_data(endpoint_path_get)

if time_result is not None:
    print("Response (GET):", time_result)


fc_request = fc_request_pb2.TonieFreshnessCheckRequest()
tonie_info = fc_request.tonie_infos.add()
tonie_info.uid = 0x0000000100000003
tonie_info.audio_id = 0

# Send a POST request with data
endpoint_path_post = 'v1/freshness-check'
fc_response_data = get_server_data(endpoint_path_post, data=fc_request.SerializeToString(), method='POST')

if fc_response_data is not None:
    print("Response (POST):", fc_response_data)
    fc_response = fc_response_pb2.TonieFreshnessCheckResponse()
    fc_response.ParseFromString(fc_response_data.encode('utf-8'))
    print("Marked UIDs:")
    for marked in fc_response.tonie_marked:
        print(format(marked, '016x'))