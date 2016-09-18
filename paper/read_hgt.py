from hgt import HGTFile
import math

def test():
    path = "/tmp/hgt/N31W089.hgt"
    h = HGTFile(path)
    d = h.read()
    print(d[0])

def get_hgt_name(lat, lng):
    # this will be replaced once mongodb is ready
    tag_lng = "E" if lng > 0 else "W"
    tag_lat = "N" if lat > 0 else "S"

    # no need to have sign any more

    # get the ceiling number
    int_lat = abs(math.floor(lat))
    int_lng = abs(math.floor(lng))

    lat_base = int_lat if lat > 0 else -int_lat
    lng_base = int_lng if lng > 0 else -int_lng

    filename = "/tmp/hgt/{0}{1:02d}{2}{3:03d}.hgt".format(tag_lat, int_lat, tag_lng, int_lng)
    return (filename, lat_base, lng_base) 



def get_height(lat, lng):
    # this will be replaced once mongodb is ready
    
    filename, lat_base, lng_base = get_hgt_name(lat, lng)

    h = HGTFile(filename)
    data = h.read()

    # need to get the no. of blocks
    size = len(data) - 1
    block_diff = 1 / size
    lng_index = round((lng - lng_base) / block_diff)
    lat_index = round((lat - lat_base) / block_diff)

    return(data[lat_index][lng_index])

if __name__ == "__main__":
    print(get_height(40.9551414, -76.8849629))
