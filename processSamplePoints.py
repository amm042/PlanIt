"""Compute network coverage given a set of basestations and defined area using
population based sampling.
"""


from pointSampler import PopulationBasedPointSampler, compute_land_area

from itwom import point_loss, ItwomParams, itwomParams_city

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

def plot_shapes(ax, shapes, filled = False, show_states = False, fc=None, alpha=0.16):
	# have to buffer the results to see how many colors to generate
	
	if fc == None:
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
		
		patches = make_patch(shp['geometry'], fc=fc(i), lw=lw, ec=ec, label=label, alpha=alpha)
		for p in patches:
			ax.add_patch(p)

def evaluate_points(num_base, loss_threshold, pointdoc, result_q):
	"called from multiprocessing"
	results = []
	cr = []
	
	# to save our results.
	connection = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015')
	db = connection.get_default_database()	

	# should be 100 point docs.
	for d in pointdoc:
		
		olddocs = db['POINTRESULTS'].find({
						'point_docid': d['_id'], 
						'num_basestations': num_base},
						{'_id': 1})
		dc = olddocs.count()
		if dc > 1:
			ods = [x['_id'] for x in olddocs]
			print("{} ({} bs) - {} has extra docs ({}), removing {}".format(d['name'], num_base, d['_id'], dc, ods[1:]))
			
			db['POINTRESULTS'].remove({'_id': {'$in': ods[1:]}})
			continue
		if dc == 1:
			print("{} ({} bs) - {} done already".format(d['name'], num_base, d['_id']))
			continue

		# select base station point(s)
		basestations = random.sample(d['points'], num_base)

		resultdoc = {			
			'name': d['name'],
			'state': d['state'],
			'area': d['area'],
			'population': d['population'],
			'point_docid': d['_id'],
			'loss_threshold': loss_threshold,
			'num_basestations': num_base,
			'num_points': len(d['points']),
			'loss_model': 'city',
			'nodes': [],
			'basestations': basestations,
			'gentime': datetime.datetime.utcnow(),
			}
		loss = []

		# can't check this way we have multiple runs of the same point with diff. base locations.
		# qry = {'point_docid': d['_id']}
		# if db['POINTRESULTS'].find(qry).limit(1).count() > 0:		
		# 	print("already have results for {}".format(d['_id']))
		# 	continue
		
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
					(p['coordinates'][0], p['coordinates'][1]), 8,
					params=itwomParams_city()) for b in basestations]
					
				min_loss = min(l)
				loss.append(min_loss)

				if min_loss < loss_threshold:
					connected += 1					
				else:
					disconnected += 1
					

				resultdoc['nodes'].append({'point':p, 'loss': l, 'min_loss': min_loss, 'connected': min_loss < loss_threshold})

		resultdoc['connected'] = connected / (connected+disconnected)
		cr.append(connected / (connected+disconnected))
		results.append(loss)

		db['POINTRESULTS'].insert_one(resultdoc)


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

	connection = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015')
	db = connection.get_default_database()	

	
	cities = list(db['POINTS'].find({"LSAD":"city"}).distinct("name"))
	print(len(cities), " cities")
	print(", ".join(["\"{}\"".format(x) for x in cities]))

	jobs = []	

	for city_name in db['POINTS'].find({"LSAD":"city"}).distinct("name"):
		pointdocs = db['POINTS'].find({"name":city_name})
		print("{} has {} points".format(
			city_name, 
			pointdocs.count()))
		#if city_name not in ['Butler', 'Carbondale', 'Corry', 'Monessen', 'Parker']:
		#if city_name not in ['Philadelphia']:
			#continue
		
		if city_name not in ['Parker']:
			continue
		# if city_name not in ["Clairton", 
		# 	"Coatesville", "Connellsville", "DuBois", "Duquesne", "Easton", "Erie", "Aliquippa", "Allentown", "Altoona", 
		# 	"Beaver Falls", "Farrell", "Arnold", "Franklin", "Jeannette", "Johnstown", "Lebanon", "Lock Haven", 
		# 	"Lower Burrell", "Latrobe", "Greensburg", "Harrisburg", "Hazleton", "Hermitage", "McKeesport", "Meadville", 
		# 	"Monongahela", "Pittsburgh", "Pittston", "Oil City", "Reading", "Pottsville", "Sunbury", "Titusville", 
		# 	"St. Marys", "Scranton", "Warren", "Washington", "Wilkes-Barre", "Williamsport", "York", "Nanticoke", 
		# 	"New Castle", "New Kensington", "Sharon"]:
		# 	print("SKIP {}".format(city_name))
		# 	continue
		

		print("getting point data for {}...".format(city_name), end="", flush=True)
		r = list(pointdocs)
		print("Done.")

		while len(jobs) > 12:
			print("waiting for: {}".format(jobs[0].name))
			jobs[0].join()
			print("{} done.".format(jobs[0].name))
			del jobs[0]

		loss_threshold = 158
		max_basestations = 6
		jobres = {}

		results = Queue()

		for num_base in range(1,max_basestations+1):
			j = Process(target=evaluate_points, 
					args=(num_base, loss_threshold, r, results), 
					name="{} {} basestations".format(city_name, num_base))
			jobs.append(j)
			j.start()

	for j in jobs:
		j.join()
		print("{} done.".format(j.name))
			# num_base, coverage = results.get()
			# print("results: ", num_base, coverage)
			# jobres[num_base] = coverage

	# 	coverage_rate = []
	# 	for num_base in range(1,max_basestations+1):
	# 		coverage_rate.append(jobres[num_base])

	# 	fig = plt.figure(figsize = (8,8))
	# 	ax = plt.subplot(111)
	# 	ax.violinplot(coverage_rate, showmeans=False, showmedians=True)
	# 	ax.set_ylabel("Connected (rate)")
	# 	ax.set_xlabel("Number of basestations")

	# plt.show()

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