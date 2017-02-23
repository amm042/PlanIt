"""Compute network coverage given a set of basestations and defined area using
population based sampling.
"""


from pointSampler import PopulationBasedPointSampler, compute_land_area

from itwom import point_loss, ItwomParams, itwomParams_city, itwomParams_average

import numpy as np

from pyproj import Geod, Proj, transform

import matplotlib.pyplot as plt
from descartes import PolygonPatch

from shapely.geometry import shape, mapping, Point
from county_lookup import state_name, county_name

from elevation import Elevation

import pymongo

from lxml import etree
import datetime
from pprint import pprint

import random

from bson import ObjectId, json_util

from multiprocessing import Process, Queue

#from threading import Thread
import logging
import os

log = logging.getLogger(__name__)


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

def evaluate_points(q, num_base, basestations,
	loss_threshold, pointdoc, bounds,
	tx_height, rx_height,
	run_id, itwomparam,
	conn_str = 'mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015',
	srtm_path = None):
	"called from multiprocessing"

	pid = os.getpid()
	# to save our results.
	logging.info("{} connecting to {}".format(pid, conn_str))
	connection = pymongo.MongoClient(conn_str)
	db = connection.get_default_database()

	elev = Elevation(srtm_path=srtm_path, mongo_str= None)

	if basestations!=None:
		num_base = len(basestations)

	logging.info("{} evaluating points for {} bs (tx {} rx {}) -- {} points".format(
			pid, num_base, tx_height, rx_height, len(pointdoc)))

	for d in pointdoc:
		rdoc = {		'name': d['name'],
						'point_docid': d['_id'],
						'loss_threshold': loss_threshold,
						'run': run_id,
						'num_basestations': num_base,
						'bounds': json_util.dumps(bounds),
						'itwomparam': itwomparam.__dict__,
						'tx_height': tx_height,
						'rx_height': rx_height}
		if basestations!= None:
			rdoc['basestations'] = basestations

		olddocs = db['POINTRESULTS'].find(rdoc)
		dc = olddocs.count()
		if dc > 1:
			ods = [x['_id'] for x in olddocs]
			logging.info("{} ({} bs) - {} has extra docs ({}), removing {}".format(d['name'], num_base, d['_id'], dc, ods[1:]))

			db['POINTRESULTS'].remove({'_id': {'$in': ods[1:]}})
			continue
		if dc == 1:
			logging.info("{} - {} done already".format(d['name'], d['_id']))
			for doc in olddocs:
				q.put(doc)
			continue

		logging.info("{} processing points for {} ({} bs) (tx {} rx {}) -- {} points".format(
			pid, d['name'], num_base, tx_height, rx_height, len(pointdoc)))
		# select base station point(s)

		if basestations == None:
			basestations = random.sample(d['points'], num_base)

		# for b in basestations:
		# 	if 'coordinates' not in b:
		# 		b['coordinates'] = shape(b['geometry']).coords[0]

		resultdoc = {
			'name': d['name'],

			'area': d['area'],
			'population': d['population'],
			'point_docid': d['_id'],
			'run': run_id,
			'loss_threshold': loss_threshold,
			'num_basestations': num_base,
			'num_points': len(d['points']),
			'itwomparam': itwomparam.__dict__,
			'bounds': json_util.dumps(bounds),
			'nodes': [],
			'grid': [],
			'basestations': basestations,
			'gentime': datetime.datetime.utcnow(),
			'tx_height': tx_height,
			'rx_height': rx_height
			}
		if 'state' in d:
			resultdoc['state'] = d['state']
		loss = []

		# can't check this way we have multiple runs of the same point with diff. base locations.
		# qry = {'point_docid': d['_id']}
		# if db['POINTRESULTS'].find(qry).limit(1).count() > 0:
		# 	print("already have results for {}".format(d['_id']))
		# 	continue

		connected = 0
		disconnected = 0

		# for b in basestations:
		# 	if 'coordinates' not in b['geometry']:
		# 		logging.info("no coordinates for {}".format(b))
		#
		# 		#convert gemoetry to geoJSON
		#
		# 		b['geometry'] = {'type': 'Point',
		# 		 'coordinates': (b['geometry']['longitude'], b['geometry']['latitude'])}
		#
		# 		logging.info("added coordinates: {}".format(b['geometry']))

		for p in d['points']:
			if p in basestations:
				#print("{} is a basestation".format(p))
				continue
			else:
				# if 'coordinates' not in p:
				# 	logging.info("no coordinates for {}".format(p))
				# 	p['coordinates'] = shape(p['geometry']).coords[0]
				# 	logging.info("added coordinates: {}".format(p['coordinates']))

				#compute loss to all basestations, and save the lowest loss path
				l = [point_loss(
					(b['geometry']['coordinates'][0], b['geometry']['coordinates'][1]), tx_height,
					(p['geometry']['coordinates'][0], p['geometry']['coordinates'][1]), rx_height,
					params=itwomparam, elev=elev)[0] for b in basestations]

				min_loss = min(l)
				loss.append(min_loss)

				if min_loss < loss_threshold:
					connected += 1
				else:
					disconnected += 1

				resultdoc['nodes'].append(
					{'point':p,
					'loss': l,
					'min_loss': min_loss,
					'connected': min_loss < loss_threshold})
		if bounds != None:
			# generate simple 10x10 grid around given bounds as well.
			xmin,ymax,xmax,ymin = (bounds['west'], bounds['north'], bounds['east'], bounds['south'])
			#g = np.mgrid[xmin:xmax:((xmax-xmin)/10), ymin:ymax:((ymax-ymin)/10)]
			# use imaginary number to include bounds
			# https://docs.scipy.org/doc/numpy/reference/generated/numpy.mgrid.html
			g = np.mgrid[xmin:xmax:11j, ymin:ymax:11j]

			# print("Generating points from bounds: {}".format(bounds))
			# print("xmin,ymax,xmax,ymin: ", xmin,ymax,xmax,ymin)
			for point in zip(*(x.flat for x in g)):
				l = [point_loss(
					(b['geometry']['coordinates'][0], b['geometry']['coordinates'][1]), tx_height,
					(point[0], point[1]), rx_height,
					params=itwomparam, elev=elev)[0] for b in basestations]

				min_loss = min(l)
				loss.append(min_loss)
				resultdoc['grid'].append({
					'point': {'geometry': mapping(Point(point))},
					'loss': l,
					'min_loss': min_loss
				})

		resultdoc['connected'] = connected / (connected+disconnected)

		db['POINTRESULTS'].insert_one(resultdoc)
		q.put(resultdoc)
	logging.info("{} finished, close db.".format(pid))
	connection.close()
	logging.info("{} done.".format(pid))

def AnalyzePoints(dbcon, connect_str, srtm_path, pointid, numBase = None,
	basestations=None, numRuns = 1,
	freq = 915.0, txHeight=5, rxHeight=1, model='city', bounds=None,
	lossThreshold = 148, **kwargs):

	pointdocs = dbcon['POINTS'].find({"_id": ObjectId(pointid)})
	logging.info("getting {} point data docs for {}...".format(
		pointdocs.count(),
		pointid))
	r = list(pointdocs)
	logging.info("Done.")

	jobres = {}

	#logging.info(dir(dbcon))

	itwomparam = itwomParams_average()
	if model == 'city':
		itwomparam = itwomParams_city()
	itwomparam.freq_mhz = freq

	q = Queue()
	jobs = []
	pcount = 0

	if basestations != None:
		pcount += 1
		j = Process(target=evaluate_points,
				args=(q, None, basestations, float(lossThreshold), r,
					bounds,
					float(txHeight), float(rxHeight),
					1, itwomparam, connect_str, srtm_path),
				name="{} {} basestations".format(pointid, len(basestations)))
		j.start()
		jobs.append(j)
	else:
		for run_id in range(int(numRuns)):
			for num_base in numBase:
				pcount += 1
				j = Process(target=evaluate_points,
						args=(q, int(num_base), None, float(lossThreshold), r,
							bounds,
							float(txHeight), float(rxHeight),
							run_id, itwomparam, connect_str, srtm_path),
						name="{} {} basestations".format(pointid, num_base))
				j.start()
				jobs.append(j)

	# must consume all results from the queue before joining the process.
	res = []
	while len(res) < pcount:
		res.append(q.get())

	for j in jobs:
		logging.info("wait for {}, {}.".format(j.pid, j.name))
		j.join()
		logging.info("{}, {} done.".format(j.pid, j.name))

	return res

if __name__=="__main__":

	connection = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015')
	db = connection.get_default_database()


	cities = list(db['POINTS'].find({"LSAD":"city"}).distinct("name"))
	print(len(cities), " cities")
	print(", ".join(["\"{}\"".format(x) for x in cities]))

	jobs = []

	# to process all cities
	#for city_name in db['POINTS'].find({"LSAD":"city"}).distinct("name"):
	#for city_name in ['St. Marys']:
	#for city_name in ['Pennsylvania']:
	#for city_name in ['Philadelphia']:
	for city_name in ['Potter']:
		pointdocs = db['POINTS'].find({"name":city_name})
		print("{} has {} points".format(
			city_name,
			pointdocs.count()))
		#if city_name not in ['Butler', 'Carbondale', 'Corry', 'Monessen', 'Parker']:
		#if city_name not in ['Philadelphia']:
			#continue

		#if city_name not in ['Parker']:
#			continue
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
		max_basestations = 12
		jobres = {}


		for num_base in range(1,max_basestations+1):
			j = Process(target=evaluate_points,
					args=(num_base, loss_threshold, r, 5, 1),
					name="{} {} basestations".format(city_name, num_base))
			jobs.append(j)
			j.start()
			#evaluate_points(num_base, loss_threshold, r, 5, 1)

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

			from pykml.factory import KML_ElementMaker as KML

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
