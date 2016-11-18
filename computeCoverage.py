"""Compute network coverage given a set of basestations and defined area using
population based sampling.



*** this file has been replaced by createSamplePoints and processSamplePoints ****
"""

raise DeprecationWarning("use createSamplePoints and processSamplePoints")


from pointSampler import PopulationBasedPointSampler, compute_land_area

from itwom import point_loss

import numpy as np

from pyproj import Geod, Proj, transform

import matplotlib.pyplot as plt
from descartes import PolygonPatch

from shapely.geometry import shape, mapping
from county_lookup import state_name, county_name

import pymongo

from pykml.factory import KML_ElementMaker as KML
from lxml import etree
import datetime
from pprint import pprint

import random

from multiprocessing import Process, Queue


def plot_contours(area, points, fig, ax, plot_legend= True, plot_points= True):

	geod = Geod(ellps='WGS84')

	xmin = area.bounds[0]
	xmax = area.bounds[2]
	ymin = area.bounds[1]
	ymax = area.bounds[3]

	X = np.linspace(xmin, xmax)
	Y = np.linspace(ymin, ymax)
	Z = np.zeros([len(Y), len(X)])

	
	mindb = 60
	maxdb = 180
	N = int((maxdb - mindb) / 10)
	v = np.linspace(mindb, maxdb, N+1)

	# generate contour volues with Shepard's Method
	for x in range(0, len(X)):
		for y in range(0, len(Y)):

			# sum of distances from this point to all points
			totaldist = sum ([geod.inv(X[x], Y[y], p[0], p[1])[2]**-8 for p in points])

			Z[y,x] = min(maxdb, sum([p[2]*(geod.inv(X[x], Y[y], p[0], p[1])[2]**-8)/totaldist for p in points]))

	#CS = ax.contour(X,Y,Z,N, linewidth=0.5, colors='k', alpha=0.3)
	CSF = ax.contourf(X,Y,Z,N, cmap=plt.cm.RdYlGn_r, alpha=1, 
		vmin = v[0], vmax=v[-1], levels=v)
		#vmin = min([p[2] for p in points]), vmax=max([p[2] for p in points]))

	if plot_legend:
		cb = fig.colorbar(CSF,ticks =v)
		cb.set_label("dB Loss")

	if plot_points:
		for p in points:
			print (p)
			ax.plot(p[0], p[1], '.', color='k', ms=4)	

def make_patch(geo, **kwargs):
	"takes a geoJSON geometry and returns something matplotlib understands"
	if geo['type'] == 'Polygon':
		return [PolygonPatch(geo,**kwargs)]
		
	elif geo['type'] == 'MultiPolygon':
		p = []
		for poly in shape(geo):
			p.append(PolygonPatch(poly, **kwargs))
			
		return p
	else:
		pprint(geo)
		raise Exception("unsupported geometry")				

def plot_shapes(ax, shapes, filled = False, show_states = False):
	# have to buffer the results to see how many colors to generate
	
	if filled:
		color_list = plt.cm.Dark2(np.linspace(0, 1, len(shapes)))
		fc = lambda x: color_list[x]
	else:
		fc = lambda x: 'none'

	states = set()
	geoid = {}
	# get the shapes covered by the coverage area.
	for i, shp in enumerate(shapes):			
		p = shp['properties']
		
		#track states we hit
		if p['STATE'] not in states:
			states.add(p['STATE'])	
		# also store the goeid so we dont plot again later
		geoid[p['GEO_ID']] = shp
		
		if p['LSAD'] == 'Tract':
			label = "{} {} [{}]".format(state_name(p['STATE']), 
						county_name(p['STATE'],p['COUNTY']), p['TRACT'])
		else:
			label = p['NAME']

		#print ("-"*10 + label + "-"*10)
		#pprint(p['population'])
		

		ec = 'black'
		lw = 1

		if 'population' in p:
			if p['population']['effective'] < 0.01:
				ec = 'blue'
				lw = 2
									#was fc = color_list[i],
		
		patches = make_patch(shp['geometry'], fc=fc(i), lw=lw, ec=ec, label=label, alpha=0.16)
		for p in patches:
			ax.add_patch(p)

def evaluate_points(num_base, pointdoc, result_q):
	"called from multiprocessing"
	results = []
	cr = []

	for d in pointdoc:				
		# select base station point(s)
		basestations = random.sample(d['points'], num_base)

		loss = []
		
		connected = 0
		disconnected = 0
		for p in d['points']:
			if p in basestations:
				#print("{} is a basestation".format(p))
				continue
			else:
				#compute loss to all basestations, and save the lowest loss path
				l = [point_loss(
					(b['coordinates'][0], b['coordinates'][1]), 15,
					(p['coordinates'][0], p['coordinates'][1]), 8) for b in basestations]
				l=min(l)
				loss.append(l)

				if l < loss_threshold:
					connected += 1
				else:
					disconnected += 1
		cr.append(connected / (connected+disconnected))
		results.append(loss)

		#if len(results) > 3:
			#break

	# fig = plt.figure(figsize = (8,8))
	# ax = plt.subplot(111)
	# if num_base  == 1:
	# 	ax.set_title("{} basestation".format(num_base))
	# else:
	# 	ax.set_title("{} basestations".format(num_base))
	# ax.violinplot(results, showmeans=False, showmedians=True)
	# ax.plot( range(2+len(results)), [loss_threshold]*(2+len(results)), '--', color='gray', lw=1)
	# ax.set_ylim((80,200))
	# ax.set_ylabel("loss (dB)")

	result_q.put( (num_base, cr))
	

if __name__=="__main__":

	generateData = True
	processData = False

	if generateData:

		connection = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015')
		db = connection.get_default_database()	
		pbps = PopulationBasedPointSampler("ca22eb30af97c6b471419d7fe22b9ce9a5d1fe8d")

		query = {'properties.LSAD': 'city', 'properties.STATE': '42'}
		for city_shp in db['GENZ2010_160'].find(query):

			num_samples = 100

			# quick check if this city already has points...
			q2 = {'state': city_shp['properties']['STATE'], 'name':city_shp['properties']['NAME']}
			have_pts = db['POINTS'].find(q2).count()
			if have_pts >= num_samples:
				print("already have {} points for {}".format(have_pts, city_shp['properties']['NAME']))				
				continue

			pts_to_gen = num_samples- have_pts
			print("generating {} points for {}".format(pts_to_gen, city_shp['properties']['NAME']))
			# number of times to generate points per location.
			for i in range(pts_to_gen):

				# bucknell
				#latitude = 40.954910
				#longitude = -76.881304
				#max_distance_meters = 10 * 1000


				# penn 
				# name = "UPenn"
				# latitude = 39.951988
				# longitude= -75.193512
				# max_distance_meters = 10 * 1000

				# compute converage area and distance
				#area, dist = pbps.get_coverage(latitude, longitude, max_distance_meters)
				#print ("got coverage")

				# get the covered shapes
				#shapes = list(pbps.get_shapes(area, dist))

				area = shape(city_shp['geometry'])
				shapes = list(pbps.get_tract_shapes_in_area(area))

				print ("got shapes")
				points = pbps.sample(1000, shapes, area)

				#for shp in shapes:
					#pprint(shp)

				print ("got points")

				covered_pop = sum([s['properties']['population']['effective'] for s in shapes])
				total_area = sum([s['properties']['area']['effective'] for s in shapes])
				
				print("shapes in {}: {}".format(city_shp['properties']['NAME'], len(shapes)))
				print("covered population: {}".format (covered_pop))
				print("total area: {}".format(total_area))
				#pprint(area)
				a = compute_land_area(area)
				print("area's area: ", a)
				

				# fig = plt.figure(figsize = (8,8), dpi=300)
				# ax = plt.subplot(111)

				# plot_shapes(ax, shapes)
				# ax.add_patch(PolygonPatch(area, fc='none',ec='red', lw='1', alpha=0.60))
				# ax.axis("equal")
				# plt.show()

				# exit()

				col = db['POINTS']

				gentime = datetime.datetime.utcnow()

				col.insert_one({			
					'gentime': gentime,
					#'center': (longitude, latitude),
					#'distance': max_distance_meters,
					'state': city_shp['properties']['STATE'],
					'name': city_shp['properties']['NAME'],
					'LSAD': 'city',
					'area': total_area,
					'population': covered_pop,
					'points': [mapping(p) for p in points],
					'shapes': shapes
				})


	if processData:
		connection = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015')
		db = connection.get_default_database()	
		col = db['POINTS']

		print("getting point data...", end="", flush=True)
		day = datetime.datetime(2016,9,23)
		r = list(col.find({"gentime": {'$gte': day, '$lt':day+datetime.timedelta(days=1)}}))
		print("Done.")

		loss_threshold = 158		
		max_basestations = 6
		jobres = {}

		results = Queue()		
		jobs = []

		for num_base in range(1,max_basestations+1):
			j = Process(target=evaluate_points, args=(num_base, r, results), name="{} basestations".format(num_base))
			jobs.append(j)
			j.start()

		for j in jobs:
			j.join()
			print("{} done.".format(j.name))
			num_base, coverage = results.get()
			print("results: ", num_base, coverage)
			jobres[num_base] = coverage

		coverage_rate = []
		for num_base in range(1,max_basestations+1):
			coverage_rate.append(jobres[num_base])

		fig = plt.figure(figsize = (8,8))
		ax = plt.subplot(111)
		ax.violinplot(coverage_rate, showmeans=False, showmedians=True)
		ax.set_ylabel("Connected (rate)")
		ax.set_xlabel("Number of basestations")

		plt.show()

	if 0:	
		loss = []
		for p in points:
			loss.append( (p.x, p.y, point_loss( (longitude,latitude), 50, (p.x, p.y), 20)))
			print(str(loss[-1]))

		# plot coverage gradient
		make_kml = True
		if make_kml:
			fig = plt.figure()
			ax = plt.Axes(fig, [0,0,1,1])
			ax.set_axis_off()
			fig.add_axes(ax)

			plot_contours(area, loss, fig, ax, plot_legend=False, plot_points=False)		

			plt.show()
			fig.savefig('coverage.png', dpi=300)

			kml = KML.Folder(
				KML.name("RF Coverage"),
				KML.GroundOverlay(
					KML.name("{},{} - {} km".format(latitude,longitude,max_distance_meters/1000.0)),
					KML.Icon(KML.href('coverage.png')),
					KML.color('b0ffffff'), #first value is alpha, ff=opaque 
					KML.LatLonBox(
						KML.north(area.bounds[1]),
						KML.south(area.bounds[3]),
						KML.east(area.bounds[2]),
						KML.west(area.bounds[0])
					)
				),
				KML.Placemark(
					KML.name('Basestation'),
					KML.Point(
						KML.extrude(1),
						KML.altitudeMode('relativeToGround'),
						KML.coordinates("{}, {}".format(longitude, latitude))
						)
					)
			)
			s= etree.tostring(kml, pretty_print=True)
			with open('coverage.kml', 'wb') as f:
				f.write(s)


		else:

			fig = plt.figure(figsize = (8,8), dpi=300)
			ax = plt.subplot(111)

			plot_shapes = False
			plot_points = False

			if plot_shapes:
				plot_shapes(ax, shapes)

			# add transmitter max area
			#ax.add_patch(PolygonPatch(area, fc='none',ec='red', lw='5', alpha=0.90))

			ax.plot(area.centroid.x, area.centroid.y, 'p', ms=12, color='blue')

			plot_contours(area, loss, fig, ax, plot_points)

			#show only the area with the contour
			
			ax.axis('equal')
			ax.set_xlim((area.bounds[0], area.bounds[2]))
			ax.set_ylim((area.bounds[1], area.bounds[3]))
			plt.show()