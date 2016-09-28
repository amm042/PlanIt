import math
from elevation import Elevation

#geopy.distance great_circle seems to give incorrect results.
#from geopy.distance import great_circle


from pyproj import Geod

class GeoPath():
	"""Construct a path between two points in lat/lon/elev across the earth.

	src -- source tuple (lon, lat, elev above ground)
	dst -- dest tuple (lon, lat, elev above ground)
	elev -- elevation provider, must have a lookup method that takes a location tuple
	resolution -- step size to use in meters
	"""
	def __init__(self, src, dst, elev = Elevation(), resolution=30):
		self.src = src
		self.dst = dst
		self.elev = elev

		self.geod = Geod(ellps='WGS84')

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