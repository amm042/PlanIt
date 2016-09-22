import math
from elevation import Elevation
from geopy.distance import great_circle

class GeoPath():
	"""Construct a path between two points in lat/lon/elev across the earth.

	src -- source tuple (lon, lat, elev above ground)
	dst -- dest tuple (lon, lat, elev above ground)
	elev -- elevation provider, must have a lookup method that takes a location tuple
	resolution -- minimum number of degress between points on the path
	"""
	def __init__(self, src, dst, elev = Elevation(), resolution=1/(2*3600.0)):
		self.src = src
		self.dst = dst
		self.elev = elev

		xsteps = abs((src[0]-dst[0])/resolution)
		ysteps = abs((src[1]-dst[1])/resolution)
		steps = int(math.ceil(min(xsteps,ysteps)))

		xslope = (dst[0]-src[0])/steps
		yslope = (dst[1]-src[1])/steps
		
		# first point is the source
		self.path = [(src[0], src[1], self.elev.lookup(src))]

		# make the path		
		for i in range(1,steps):
			x = src[0]+i*xslope
			y = src[1]+i*yslope

			self.path.append((x,y,self.elev.lookup((x,y))))

		# add destn location and elev
		self.path.append((dst[0], dst[1], self.elev.lookup(dst)))
		
	
	def distance(self):
		"length of path across the earth in meters"
		return self.point_distance(self.path[0], self.path[-1])
	def point_distance(self, a, b):
		"distance between two points on the earth using the gread circle"
		return great_circle(a,b).meters