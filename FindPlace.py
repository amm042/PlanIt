import pymongo
from county_lookup import state_num

from shapely.geometry import shape

def findPlace(placename, state):
    db = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015').get_default_database()
    col = db['GENZ2010_160']

    c = col.find({
        'properties.NAME': placename,
        'properties.STATE': state
        })

    for res in c:
        sh = shape(res['geometry'])
        yield sh.centroid

if __name__ == "__main__":
    for p in findPlace('Harrisburg', state_num('PA')):
        print(p)
