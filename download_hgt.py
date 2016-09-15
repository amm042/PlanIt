import re
import os
import requests
import time
from requests.auth import HTTPBasicAuth
import zipfile
import io


URL = "https://cloud.sdsc.edu/v1/AUTH_opentopography/Raster/SRTM_GL3/"
if os.path.isfile("down.html"):
    with open("down.html") as f:
        html = f.read()
else:
    response = requests.get(URL)
    with open("down.html", "w+") as f:
        html = response.text
        f.write(html)
        
urls = re.findall(r'href=[\'"]?([^\'" >]+)', html)
urls = [x for x in urls if x.endswith("hgt.zip")]
for url in urls:
    path = os.path.join("/tmp/temp", url.split(".")[0] + ".hgt")
    if os.path.isfile(path) or os.path.isdir(path):
        print("skip", url)
        continue
    else:
        zip_url = URL + url
        print(zip_url)
        # password: 
        # cookie = {"DATA": "V9nc4Zg9BGcAAGByjLkAAABc"}
        r = requests.get(zip_url) #, cookies=cookie)
        if r.status_code != 200:
            print("error", r.status_code)
            break
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(path="/tmp/temp")
        #with open(path, "wb+") as f:
        #    f.write(r.content)
        time.sleep(10)  # don't push the server too hard
