import math
from elevation import Elevation

#geopy.distance great_circle seems to give incorrect results.
#from geopy.distance import great_circle


from pyproj import Geod

from multiprocessing import Process, Queue
import gevent
from bson import json_util

import logging
class GeoPath():
	"""Construct a path between two points in lat/lon/elev across the earth.

	src -- source tuple (lon, lat, elev above ground)
	dst -- dest tuple (lon, lat, elev above ground)
	elev -- elevation provider, must have a lookup method that takes a location tuple
	resolution -- step size to use in meters

	"""
	def __init__(self, src = None, dst = None, path = None, elev = None, resolution=30, async=False, **kwargs):
		
		self.geod = Geod(ellps='WGS84')
		if elev == None:			
			self.elev = Elevation(**kwargs)

		self.src = src
		self.dst = dst
		self.elev = elev

		if path == None:		
			az1, az2, dist = self.geod.inv(
				src[0], src[1], 
				dst[0], dst[1])
			#print("az = {}, {} dist = {}".format(az1, az2, dist))

			

			# xsteps = abs((src[0]-dst[0])/resolution)
			# ysteps = abs((src[1]-dst[1])/resolution)
			# steps = int(math.ceil(min(xsteps,ysteps)))

			# xslope = (dst[0]-src[0])/steps
			# yslope = (dst[1]-src[1])/steps

			npts = int(dist / resolution)
			
			#print("src={}, dst={}, npts={}".format(src, dst, npts))

			if not async:
				# first point is the source
				self.path = [(src[0], src[1], self.elev.lookup(src))]
				for lon,lat in self.geod.npts(src[0], src[1], dst[0], dst[1], npts):
					self.path.append( (lon,lat, self.elev.lookup( (lon,lat) ) ) )
				# make the path		
				# for i in range(1,steps):
				# 	x = src[0]+i*xslope
				# 	y = src[1]+i*yslope

				# add destn location and elev
				self.path.append((dst[0], dst[1], self.elev.lookup(dst)))
			else:
				logging.info("geopath creating npts async.")

				def worker(obj, npts):
					obj.npts = obj.geod.npts(obj.src[0], obj.src[1], obj.dst[0], obj.dst[1], npts)
				def proc_worker(q, src, dst, npts, geod):
					q.put(geod.npts(src[0], src[1], dst[0], dst[1], npts))

				self.q = Queue()
				self.p = Process(target = proc_worker, args=(self.q, src, dst, npts, self.geod))
				self.p.start()
				#self.g = gevent.spawn(worker, self, npts)
				#self.g.start()

				logging.info("geopath created with async process.")
		else:
			self.path = path
			self.src = path[0]
			self.dst = path[-1]
			
	def async(self):
		"return the path asynchronously"
		logging.info("geopath wait for npts.")
		yield ''
		while self.q.empty():
			gevent.sleep(1)
			yield ' '

		logging.info("geopath proc compelte.")	
		#self.g.join() # for god measure
		self.npts = self.q.get()
		logging.info("geopath proc joined.")
		for lon,lat in self.npts:
			yield ( json_util.dumps((lon, lat, self.elev.lookup( (lon, lat) )) ) )
	
	def distance(self):
		"length of path across the earth in meters"
		return self.point_distance(self.path[0], self.path[-1])
	def point_distance(self, a, b):
		"distance between two points on the earth in meters"
		return self.geod.inv(a[0],a[1],b[0],b[1])[2]

if __name__=="__main__":

	# breakiron
	a = (-76.881249, 40.954899)
	
	# house
	b = (-76.897619, 40.955291)

	g = GeoPath(a,b, resolution = 30)
	print("a: {}".format(a))
	print('path has {} points: {}'.format(len(g.path), g.path))
	print("b: {}".format(b))
	print("total distance is {} meters".format(g.distance()))