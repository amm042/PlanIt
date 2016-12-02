import requests

from bson import json_util
import logging
#logging.basicConfig(level=logging.DEBUG)

def api_req(service, url="https://www.eg.bucknell.edu/planit/api/", stream=False, **kwargs):
    "make a generic api request"
    
    p = {'key': 'eyJhbGciOiJIUzI1NiJ9.IjU4M2M3Y2EyNDdlZmE2MzgwMmI1NzNjOCI._fMAFEPDDGiAv9z6uhAKZVeBQx8TyCH1WzkzZzuXQew'}
    p.update(kwargs)
    if stream == True:
        r = requests.post(url+service, json=p, stream=stream)
        for chunk in r.iter_content(1*1024):
            # server sends spaces to keep the connection alive while thinking.
            if chunk != b' ':
                yield json_util.loads(chunk.decode('utf-8'))
    else:        
        r = requests.post(url+service, json=p)
        try:
            js = r.json()
        except Exception as x:
            raise Exception('Server response: ' + r.text)
            
        if 'result' in js:
            yield js['result']
        else:
            raise Exception('Server error: ' + r.text)

def get_elevation(lat, lon):
    # even unstreamed, api_req is a generator (thanks python)
    # calling next gets the first and only value if we don't want to stream
    return next(api_req('elevation', lat=lat, lon=lon))

def get_path(src, dst):
    return api_req('geopath', src=src, dst=dst, stream=True)

def get_itwom():    
    return next(api_req('itwomparams'))

def get_loss(point_to_point = True, **kwargs):
    """default to point to point loss

    you must specify kwargs (src, dst) or path.

    """
    if point_to_point == True:
        return next(api_req('pathloss', stream=True, 
                point_to_point=point_to_point, **kwargs))
    else:
        return api_req('pathloss', stream=True, 
                point_to_point=point_to_point, **kwargs)

# turn on to test get elevation
if 1:
    for lon,lat in [(-76.881249, 40.954899),
    	            (-76.897619, 40.955291),
                    (-106.013942, 39.473847)]:
        print('{}, {} has elevation = {} meters'.format(
            lat,
            lon,
            get_elevation(lat,lon)))


a=(-76.881249, 40.954899)
b=(-76.897619, 40.955291)
#b=(-76.870814, 40.271777,)
#b=(-106.013942, 39.473847)
print("from {} --> {} == ".format(a,b))

# turn on to test get path and loss along path
if 1:    
    path = []
    for point in get_path(a,b):
        print("\t{}".format(point))
        path.append(point)

    itwomparam = get_itwom()
    print ("Itwom default parameters: {}".format(itwomparam))
    #change a parameter for fun
    itwomparam['freq_mhz'] = 2000
    print ("Using Itwom parameters: {}".format(itwomparam))
    # make a call to path loss with given path
    print ("path loss using path and new params: ", get_loss(path=path, itowmparam= itwomparam))
    
    for loc, loss in zip (path, get_loss(path=path, itowmparam=itwomparam, point_to_point=False)):
        print ("{} loss = {}".format(loc, loss))

# test direct point to point path loss
if 1:
    print ("point to point path loss w/o path: {}".format(get_loss(src=a,dst=b)))      

# test full point to point path loss
if 1:
    print ("full path loss w/o path:")
    for x in get_loss(src=a,dst=b,point_to_point=False):
        print(x)

