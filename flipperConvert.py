#!/usr/bin/python3

import yaml
import os
import glob

flipper_dumps_folder = 'work/flipper/SLIX_*.nfc'
for file_path in glob.glob(flipper_dumps_folder):
    # Extract the reversed UID from the filename
    filename = os.path.basename(file_path)
    uid = filename.split('_')[1].split('.')[0]
    ruid = bytes.fromhex(uid)[::-1].hex()

    #print(f"File: {filename}, ruid: {ruid}")
    with open(file_path, "r") as file:
        for line in file:
            if line.startswith("Data Content: "):
                data_content = line.split(": ")[1]
                break
    if data_content is not None:
        auth = data_content.replace(" ", "").replace("\n", "").lower()
        if len(auth) != 64:
            print(f'Auth has invalid length {len(auth)}, {repr(auth)}')
        else:
            print(f'{ruid},{auth}')