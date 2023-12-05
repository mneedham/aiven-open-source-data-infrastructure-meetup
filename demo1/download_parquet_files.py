import requests
import os
import shutil
import time
import dask
from tqdm import tqdm

def download_file(url, local_filename):
    with requests.get(url, stream=True, allow_redirects=True) as r:
        r.raise_for_status()
        total_length = int(r.headers.get('content-length', 0))
        chunk_size = 1024  # 1 Kilobyte

        with open(local_filename, 'wb') as f:
            for chunk in tqdm(r.iter_content(chunk_size), total=total_length/chunk_size, desc=local_filename):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)                    
    return local_filename


def download(file):
    url = f"https://huggingface.co/datasets/vivym/midjourney-messages/resolve/main/data/{file}?download=true"
    print(f"Downloading {url}")        
    local_filename = download_file(url, f"data/{file}")
    return local_filename

files_to_download = [f"0000{index:0>2}.parquet" for index in range(0, 56)]

# for file in files_to_download:   
#     if not os.path.isfile(f"data/{file}"):
#         download(file)        
#     else:
#         print(f"File {file} already exists")


lazy_results = []
for file in files_to_download:   
    if not os.path.isfile(f"data/{file}"):
        result = dask.delayed(download)(file)
        lazy_results.append(result)
    else:
        print(f"File {file} already exists")

dask.persist(*lazy_results)