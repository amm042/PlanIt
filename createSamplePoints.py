"""Compute network coverage given a set of basestations and defined area using
population based sampling.
"""


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

	

if __name__=="__main__":

	connection = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015')
	db = connection.get_default_database()	
	pbps = PopulationBasedPointSampler("ca22eb30af97c6b471419d7fe22b9ce9a5d1fe8d")

	#query = {'properties.LSAD': 'city', 'properties.STATE': '42'}
	#for container_shape in db['GENZ2010_160'].find(query):
	#query = {'properties.NAME':'Pennsylvania'}
	#for container_shape in db['GENZ2010_040'].find(query):

	query = {'properties.NAME': 'Potter', 'properties.STATE': '42'}
	for container_shape in db['GENZ2010_050'].find(query):

		print("sampling ", container_shape['properties'])

		num_samples = 10
		# 1000 for citys
		# 10000 for states
		num_points_per_sample = 1000

		# quick check if this city already has points...
		q2 = {'state': container_shape['properties']['STATE'], 'name':container_shape['properties']['NAME']}
		have_pts = db['POINTS'].find(q2).count()
		if have_pts >= num_samples:
			print("already have {} points for {}".format(have_pts, container_shape['properties']['NAME']))				
			continue

		pts_to_gen = num_samples- have_pts
		print("generating {} points for {}".format(pts_to_gen, container_shape['properties']['NAME']))
		if pts_to_gen < 1:
			continue

		# compute converage area and distance
		#area, dist = pbps.get_coverage(latitude, longitude, max_distance_meters)
		#print ("got coverage")

		# get the covered shapes
		#shapes = list(pbps.get_shapes(area, dist))

		area = shape(container_shape['geometry'])

		centroid = area.centroid
		bounds = area.bounds

		print ("got area centroid={}, bounds={}".format(centroid, bounds))

		shapegen = pbps.get_tract_shapes_in_area(area, limit=None)
		shapes = []
		# grow area if any tract is outside of the initial area
		for shp in shapegen:
			shobj = shape(shp['geometry'])
			if not area.contains(shobj):
				print("growing area to fully contain {}".format(shp['properties']['label']))
				area = area.union(shobj)
			shapes.append(shp)

		# area is now the union of all shapes to accoutn for when census tract is larger than place shape
		#area = shape(shapes[0]['geometry'])
		#for shp in shapes[1:]:
	#		area = area.union(shape(shp['geometry']))

		print ("sampling points.")		
		# number of times to generate points per location.
		for i in range(pts_to_gen):

			points = pbps.sample(num_points_per_sample, shapes, area)

			#for shp in shapes:
				#pprint(shp)

			print ("got points {}".format(i))

			covered_pop = sum([s['properties']['population']['effective'] for s in shapes])
			total_area = sum([s['properties']['area']['effective'] for s in shapes])
			
			print("shapes in {}: {}".format(container_shape['properties']['NAME'], len(shapes)))
			print("covered population: {}".format (covered_pop))
			print("total area: {}".format(total_area))
			#pprint(area)
			a = compute_land_area(area)
			print("area's area: ", a)
		
			gentime = datetime.datetime.utcnow()

			db['POINTS'].insert_one({			
				'gentime': gentime,
				#'center': (longitude, latitude),
				#'distance': max_distance_meters,
				'state': container_shape['properties']['STATE'],
				'name': container_shape['properties']['NAME'],
				'LSAD': container_shape['properties']['LSAD'],
				'area': total_area,
				'population': covered_pop,
				'points': [mapping(p) for p in points],
				#'shapes': shapes  # for states shapes are too big to store in this doc, just store doc ids
				'shape_ids': [shp['_id'] for shp in shapes]
			})



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