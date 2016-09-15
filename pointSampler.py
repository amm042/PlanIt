"""MongoDB can perform spatial queries on GeoJSON objects, 
try a query to select census tracts by distance.

"""
import glob
from pprint import pprint

import fiona
from shapely.geometry import shape, Point
from descartes import PolygonPatch
import numpy as np

import matplotlib.pyplot as plt
from pyproj import Geod

import pymongo
from bson.son import SON
from bson.json_util import dumps

from census import Census

from county_lookup import state_name, county_name


class PopulationBasedPointSampler():
	def __init__(self, census_apikey="ca22eb30af97c6b471419d7fe22b9ce9a5d1fe8d"):
		# to lookup populations by census tract
		self.census = Census(census_apikey)
		# for distance calculations on the earth's surface
		self.geod = Geod(ellps='WGS84')

		# mongodb with loaded GENZ2010 cartographic boundary files
		self.connection = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015')
		self.db = self.connection.get_default_database()
		# use the database of summary level 140 = state-county-census tract
		self.col = self.db['GENZ2010_140']

	def get_coverage(self, latitude = 40.954910, longitude = -76.881304, max_distance_meters = 15 * 1000):

		# compute lat/lon at max distance with heading of 0 degrees (latitude will be different)
		elon, elat, eaz = self.geod.fwd(longitude, latitude, 0, max_distance_meters)
		# now we can construct a circle of max distance
		max_area = Point(longitude, latitude).buffer(abs(elat-latitude))
		return max_area, max_distance_meters

	def get_shapes_for_state(self, state):
		query = {'properties.STATE': state}
		return self.db.GENZ2010_140.find(query)

	def get_shapes(self, max_area, max_distance_meters):
		"return the shapes [census tracts] that touch the center of max_area + max_distance"		

		query = {'geometry': {'$near': SON([('$geometry', 
			SON([('type', 'Point'), ('coordinates', [longitude, latitude])])), 
				('$maxDistance', max_distance_meters)])}}

		for shp in self.db.GENZ2010_140.find(query):
			# add population to properties
			p = shp['properties']
		
			# for later use
			p['label'] = "{} {} [{}]".format(state_name(p['STATE']), 
					county_name(p['STATE'],p['COUNTY']), p['TRACT'])

			pop = {}
			# lookup population and area	
			raw_pop = int(self.census.sf1.state_county_tract("P0010001", p['STATE'], 
						p['COUNTY'], p['TRACT'])[0]["P0010001"])
			pop['raw'] = raw_pop
			#print("raw population: {}".format(raw_pop))

			# compute area in our radius
			county_shape = shape(shp['geometry'])
			isect = county_shape.intersection(max_area)

			# save the intersection for later use.
			shp['intersection'] = isect

			pop['area'] = county_shape.area
			frac_contained = float(isect.area) / float(county_shape.area)
			pop['frac_contained'] = frac_contained
			#print("contained: {}".format(frac_contained))

			# compute effective population
			#print("contained population: {}".format(frac_contained * raw_pop))
			pop['effective'] = frac_contained * raw_pop

			p['population'] = pop

			# filter out areas with very low population
			# the mongodb geo query may be not exact
			if frac_contained*raw_pop < 0.1: 
				print ("WARN: clipping: {}".format(p['label']))
				pprint(pop)
				continue

			yield shp

	def random_point_inside(self, shape):
		"return a random location contained inside shape"

		# get the bounding box.
		minx, miny, maxx, maxy = shape.bounds
		range_x = maxx- minx
		range_y = maxy- miny

		while True:
			# normal distribution with std.dev=range and mean = centroid of shape.
			x = range_x * np.random.randn() + shape.centroid.x
			y = range_y * np.random.randn() + shape.centroid.y
			p = Point(x,y)
			if shape.contains(p):
				break

		return p

	def sample(self, n, shapes, max_area):
		"return a sample of n random points within the given area sampled from shapes using their effective pop"
		tot_pop = 0
		for s in shapes:
			tot_pop += s['properties']['population']['effective']
		print('total effective population: {}'.format(tot_pop))

		# compute sample rates from contained population rate
		rates = [0.0]* len(shapes)
		for i,s in enumerate(shapes):
			rates[i] = float(s['properties']['population']['effective']) / tot_pop
			print("rate is {} from {}".format(rates[i], s['properties']['label']))
		
		#sample using population rate
		s = np.random.choice(shapes, size=n, replace=True, p=rates)

		pts = []
		for q in s:
			pts.append (self.random_point_inside(q['intersection']))
			#print("[{:3}] -- {}: {}".format(i, q['properties']['label'], pts[i]))
		return pts


def make_patch(geo, **kwargs):
	"takes a geoJSON geometry and returns something matplotlib understands"
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
if __name__ == "__main__":


	pbps = PopulationBasedPointSampler("ca22eb30af97c6b471419d7fe22b9ce9a5d1fe8d")
	fig = plt.figure(figsize=(4.25,4))
	ax = plt.subplot(111)

	
	states = set()
	geoid = {}

	latitude = 40.954910
	longitude = -76.881304
	max_distance_meters = 15 * 1000

	# compute converage area and distance
	area, dist = pbps.get_coverage(latitude, longitude, max_distance_meters)
	
	# have to buffer the results to see how many colors to generate
	results = list(pbps.get_shapes(area, dist))
	color_list = plt.cm.Dark2(np.linspace(0, 1, len(results)))

	# get the shapes covered by the coverage area.
	for i, shp in enumerate(results):			
		p = shp['properties']
		
		#track states we hit
		if p['STATE'] not in states:
			states.add(p['STATE'])	
		# also store the goeid so we dont plot again later
		geoid[p['GEO_ID']] = shp
		
		label = "{} {} [{}]".format(state_name(p['STATE']), 
					county_name(p['STATE'],p['COUNTY']), p['TRACT'])

		#print ("-"*10 + label + "-"*10)
		#pprint(p['population'])
		
		ec = 'black'
		lw = 2
		if p['population']['effective'] < 0.01:
			ec = 'blue'
			lw = 4
		patches = make_patch(shp['geometry'], fc=color_list[i], lw=lw, ec=ec, label=label)
		for p in patches:
			ax.add_patch(p)


	# add transmitter max area
	ax.add_patch(PolygonPatch(area, fc='green',ec='red', lw='5', alpha=0.5))


	# get 100 density based samples from these shapes
	nodes = pbps.sample(1000, results, area)

	for n in nodes:
		ax.plot(n.x, n.y, '+', markersize=12, color='black')

		
	with open("points.json", 'w') as f:
		f.write (dumps([(n.x, n.y) for n in nodes]))
 

	#ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15),
	 #         fancybox=True, shadow=True, ncol=1)

	#	cent = shape(shp['geometry']).centroid
		#print("centroid is: {}".format(cent))
				
	if 1: #turnd off to make faster
		# plot the rest of the sate in grayscale

		#s= plt.Circle( (longitude, latitude), abs(latitude-elat), color='black', lw=3, ls='-', fill=False)
		#ax.add_artist(s)

		print("getting the rest of the tracts...")
		# draw all states we plotted but with low oppacity
		for state in states:
			
			results = list(pbps.get_shapes_for_state(state))
			color_list = plt.cm.gray(np.linspace(0, 1, len(results)))

			print("plotting the rest of the tracts...")
			for i,shp in enumerate(results):
				
				patches = make_patch(shp['geometry'], alpha=0.15, fc=color_list[i], ec='black', lw=0.5, label=label)
				for p in patches:
					ax.add_patch(p)

	ax.axis('scaled')
	print("done.")



	if 0:
		fig = plt.figure(figsize=(4.25,4))
		ax = plt.subplot(111)

		print("getting CO rest of the tracts...")
		# draw all states we plotted but with low oppacity	
		for state in ['08']:
			query = {'properties.STATE': state}
			results = list(db.GENZ2010_140.find(query))
			color_list = plt.cm.Set1(np.linspace(0, 1, len(results)))

			print("plotting the rest of the tracts...")
			for i,shp in enumerate(results):			
				patches = make_patch(shp['geometry'], alpha=0.35, fc=color_list[i], ec='black', lw=1, label=label)
				for p in patches:
					ax.add_patch(p)
		ax.axis('scaled')

	plt.show()
