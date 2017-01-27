import pymongo
from county_lookup import state_num

#from shapely.geometry import shape
from shapely.geometry import mapping, shape, Point, Polygon, MultiPolygon

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
    # for p in findPlace('Harrisburg', state_num('PA')):
    #     print(p)
    import pprint
    db = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015').get_default_database()
    col = db['GENZ2010_040']

    states = {'01': 'Alabama', '02': 'Alaska', '04': 'Arizona', '05': 'Arkansas',
'06': 'California', '08': 'Colorado', '09': 'Connecticut', '10': 'Delaware', '11': 'District of Columbia',
'12': 'Florida', '13': 'Georgia', '15': 'Hawaii', '16': 'Idaho', '17': 'Illinois',
'18': 'Indiana', '19': 'Iowa', '20': 'Kansas', '21': 'Kentucky', '22': 'Louisiana',
'23': 'Maine', '24': 'Maryland', '25': 'Massachusetts', '26': 'Michigan', '27': 'Minnesota',
'28': 'Mississippi', '29': 'Missouri', '30': 'Montana', '31': 'Nebraska', '32': 'Nevada',
'33': 'New Hampshire', '34': 'New Jersey', '35': 'New Mexico', '36': 'New York',
'37': 'North Carolina', '38': 'North Dakota', '39': 'Ohio', '40': 'Oklahoma', '41': 'Oregon',
'42': 'Pennsylvania', '44': 'Rhode Island', '45': 'South Carolina', '46': 'South Dakota',
'47': 'Tennessee', '48': 'Texas', '49': 'Utah', '50': 'Vermont', '51': 'Virginia',
'53': 'Washington', '54': 'West Virginia', '55': 'Wisconsin', '56': 'Wyoming',
'72': 'Puerto Rico'}
    if states == None:
        for stname in col.distinct( 'properties.NAME'):
            doc = col.find({'properties.NAME': stname}, {'_id':0, 'properties.STATE':1}).next()
            states[doc['properties']['STATE']]=stname


    # compute a bounding box for all states
    for stid, stname in states.items():
        print("getting bounding box for {}".format(stname))

        shp = shape(col.find({'properties.STATE': stid}).next()['geometry'])

        x = mapping(shp.centroid)
        states[stid] = {'name': stname, 'bounds': list(shp.bounds), 'centroid': {'coordinates': list(x['coordinates']), 'type': x['type']}}



    pprint.pprint(states)
