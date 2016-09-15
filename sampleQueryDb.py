"""MongoDB can perform spatial queries on GeoJSON objects, 
try a query to select census tracts by distance.

"""
import glob
import fiona
import pymongo
from shapely.geometry import shape, Point

from pprint import pprint
from bson.son import SON

from county_lookup import state_name, county_name

import matplotlib.pyplot as plt
from descartes import PolygonPatch
import numpy as np

from pyproj import Geod

from census import Census

def make_patch(geo, **kwargs):
	if geo['type'] == 'Polygon':
		return [PolygonPatch(shp['geometry'],**kwargs)]
		
	elif geo['type'] == 'MultiPolygon':
		p = []
		for poly in shape(geo):
			p.append(PolygonPatch(poly, **kwargs))
			
		return p
	else:
		pprint(geo)
		raise Exception("unsupported geometry")		

census = Census("ca22eb30af97c6b471419d7fe22b9ce9a5d1fe8d")

# for distance calculations on the earth's surface
geod = Geod(ellps='WGS84')

db = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015').get_default_database()
col = db['GENZ2010_140']

latitude = 40.954910
longitude = -76.881304
max_distance = 5000 #meters

# compute lat/lon at max distance with heading of 0 degrees (latitude will be different)
elon, elat, eaz = geod.fwd(longitude, latitude, 0, max_distance)
# now we can construct a circle of max distance
max_area = Point(longitude, latitude).buffer(abs(elat-latitude))

query = {'geometry': {'$near': SON([('$geometry', 
	SON([('type', 'Point'), ('coordinates', [longitude, latitude])])), ('$maxDistance', max_distance)])}}

results = list(db.GENZ2010_140.find(query))

fig = plt.figure(figsize=(4.25,4))
ax = plt.subplot(111)





color_list = plt.cm.Dark2(np.linspace(0, 1, len(results)))

states = set()
geoid = {}
for i, shp in enumerate(results):
		
	p = shp['properties']
	#track states we hit
	if p['STATE'] not in states:
		states.add(p['STATE'])	
	# also store the goeid so we dont plot again later
	geoid[p['GEO_ID']] = shp
	
	label = "{} {} [{}]".format(state_name(p['STATE']), 
				county_name(p['STATE'],p['COUNTY']), p['TRACT'])

	print ("-"*10 + label + "-"*10)

	# lookup population and area	
	raw_pop = int(census.sf1.state_county_tract("P0010001", p['STATE'], p['COUNTY'], p['TRACT'])[0]["P0010001"])

	print("raw population: {}".format(raw_pop))

	# compute area in our radius
	county_shape = shape(shp['geometry'])
	isect = county_shape.intersection(max_area)

	frac_contained = isect.area / county_shape.area
	print("contained: {}".format(frac_contained))

	# compute effective population
	print("contained population: {}".format(frac_contained * raw_pop))

	patches = make_patch(shp['geometry'], fc=color_list[i], lw=2, ec='black', label=label)
	for p in patches:
		ax.add_patch(p)

# add transmitter max area
ax.add_patch(PolygonPatch(max_area, fc='green',ec='red', lw='5', alpha=0.5))


ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15),
          fancybox=True, shadow=True, ncol=1)

#	cent = shape(shp['geometry']).centroid
	#print("centroid is: {}".format(cent))
			
if 0: #turnd off to make faster

	s= plt.Circle( (longitude, latitude), abs(latitude-elat), color='black', lw=3, ls='-', fill=False)
	ax.add_artist(s)

	print("getting the rest of the tracts...")
	# draw all states we plotted but with low oppacity
	for state in states:
		query = {'properties.STATE': state}
		results = list(db.GENZ2010_140.find(query))
		color_list = plt.cm.gray(np.linspace(0, 1, len(results)))

		print("plotting the rest of the tracts...")
		for i,shp in enumerate(results):
			
			patches = make_patch(shp['geometry'], alpha=0.15, fc=color_list[i], ec='black', lw=2, label=label)
			for p in patches:
				ax.add_patch(p)

ax.axis('scaled')
print("done.")
plt.show()
