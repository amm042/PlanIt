import os
import json
from hgt import HGTFile

def find_files(dir_name):
    hgt_files = [os.path.join(dir_name, f) for f in os.listdir(dir_name) if f.endswith(".hgt")]
    return hgt_files


def output_json(filename):
    f = HGTFile(filename)
    data = f.read()

    dir_name, filename = os.path.split(filename)
    lat = int(filename[1:3])
    lng = int(filename[4:7])

    if filename[0] == "S":
        lat = -lat

    if filename[3] == "W":
        lng = -lng

    size = len(data[0]) - 1
    degree = 1 / size
    points = [None for i in range(size * size)] # preallocate the memory sapce
    for j in range(size):
        for i in range(size):
            p_lat = lat + j * degree / 2
            p_lng = lng + i * degree / 2
            lng_upper = lng + 1
            lat_upper = lat + 1
            if lng_upper > 180:
                lng_upper = 180 - lng_upper
            elev = data[j][i]
            gj =  { "type": "Feature",
                    "bbox": [lng, lat, lng_upper, lat_upper],
                    "geometry": {
                        "type": "Point",
                        "coordinates": [p_lng, p_lat, elev]
                    }
                  }
            points[i + j * size] = gj
    return json.dumps(points)


if __name__ == "__main__":
    hgt_files = find_files("/tmp/hgt")  # need to change this dir
    str_json = output_json(hgt_files[0])
    print(str_json)    
