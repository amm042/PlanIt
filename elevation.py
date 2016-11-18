
import numpy

from osgeo import gdal
import osgeo.gdalconst as gdalconst
from affine import Affine

import requests
import os.path

import pymongo
import gridfs
import traceback
import math

import time
import zipfile

import multiprocessing

locker = multiprocessing.Lock()
cache = {}

class Elevation():
	""" Find the elevation of a given lat/lon location on earth using SRTM data
		
		srtm_path -- the local path to cache STRM tiles
		mongo_str -- connection string to mongodb server / gridfs containing the STRM tiles.
	"""

	def __init__(self, srtm_path="./SRTM", zip_path="../../SRTMGL1/", 
		mongo_str="mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015"):

		if mongo_str != None:
			self.db = pymongo.MongoClient(mongo_str).get_default_database()
			self.strm = self.db['STRMGL1']
			self.gfs = gridfs.GridFS(self.db)
		else:
			self.db = None
			self.strm = None
			self.gfs = None

		self.srtm_path = srtm_path
		self.zip_path = zip_path
		
		if not os.path.exists(srtm_path):
			os.makedirs(srtm_path)
	

		self.url = 'http://ned.usgs.gov/epqs/pqs.php'
		#?x=-76.88670566666667&y=40.95502966666667&units=Meters&output=json

	def geoToCoord(self, p, a):
		"convert the geo point (lon,lat) p to row, col value using the given affine transform"
		# http://www.perrygeo.com/python-affine-transforms.html
		
		col,row = ~a*(p[0], p[1])
		
		# print("raw affine: ",col,row)
		# convert to ints. the transform alread references the pixel center so truncate gives
		# nearest pixel
		return int(row), int(col)

	def lookup_ws(self, p):
		"lookup elev using the web service (used to validate the lookup function)"

		# this failes sometimes, retry if failed.
		for retries in range(15):
			try:
				r = requests.get(self.url, params={	'x': p[0],
												'y': p[1],
												'units': 'Meters',
												'output': 'json'} )
				if r.status_code == requests.codes.ok:
					j = r.json()
					print(j)
					return j['USGS_Elevation_Point_Query_Service']["Elevation_Query"]['Elevation']
				else:
					print(r.text())
			except:
				# likely a timeout exception
				traceback.print_exc()
				time.sleep(5*retries)

	def lookup(self, p):
		"return elevation for point p (lon,lat)"
		#print("lookup for {}".format(p))
		global cache, locker

		# don't allow multiple threads to create new files, let one thread do it, the others will pickup the local file.
		# locker.acquire()

		try:	

			if p[0] < 0:
				ew = 'W'
			else:
				ew = 'E'

			if p[1] < 0:
				ns = 'S'
			else:
				ns = 'N'

			# construct STRM tile
			tile = "{}{:02d}{}{:03d}.hgt".format(
				ns, int(abs(math.floor(p[1]))),
				ew,int(abs(math.floor(p[0]))))

			ziptile= "{}{:02d}{}{:03d}.SRTMGL1.hgt.zip".format(
				ns, int(abs(math.floor(p[1]))),
				ew,int(abs(math.floor(p[0]))))
			
			# load into memory cache
			if not tile in cache:			
				local_tilefile = os.path.join(self.srtm_path, tile)
				if not os.path.exists(local_tilefile):	

					if os.path.exists(os.path.join(self.zip_path, ziptile)):

						with zipfile.ZipFile(os.path.join(self.zip_path, ziptile)) as zf:
							
							for zipcontent in zf.namelist():
								print("unzipping {} --> {}".format(
									os.path.join(self.zip_path, ziptile),
									os.path.join(self.srtm_path, zipcontent)))

								data = zf.read(zipcontent)
								with open(os.path.join(self.srtm_path, zipcontent), 'wb') as outf:
									outf.write(data)

					else:

						print("need tile: {} from gridfs".format(tile))
						fp = self.gfs.find_one({'filename':tile})
						if fp == None:
							print("Warning tile {} not found on gridfs, assuming sea level (zeros)".format(tile))
							import time
							time.sleep(3)
						else:
							print("getting {} bytes from {} to {}.".format(fp.length, fp, local_tilefile))							
							with open(local_tilefile, 'wb') as lfp:
								lfp.write(fp.read())
				
				if os.path.exists(local_tilefile):
					# load from disk to memory cache
					print("loading tile: {}".format(local_tilefile))
					d = gdal.Open(local_tilefile, gdalconst.GA_ReadOnly)
					r1 = d.GetRasterBand(1)
					cache[tile] = {
						'rows': d.RasterXSize,
						'cols': d.RasterYSize,
						'transform': Affine.from_gdal(*d.GetGeoTransform()),
						'raster': r1.ReadAsArray(0,0,d.RasterXSize, d.RasterYSize)
					}
					# gdal doesn't support with or del, this is how they say to close the dataset
					# http://www.gdal.org/gdal_tutorial.html
					d = None
					r1 = None
				else:
					# create a zero elevation tile (tile not found on gridfs)
					cache[tile] = {
						'rows': 3601,
						'cols': 3601,
						'transform': Affine.identity(), # doesn't really matter
						'raster': numpy.zeros((3601, 3601))
					}
			
			row,col = self.geoToCoord((p[0],p[1]), cache[tile]['transform'])
			
			#print("transform = {}".format(self.cache[tile]['transform']))
			# mrow = self.cache[tile]['rows']
			# mcol = self.cache[tile]['cols']
			# print("{} == {} has elev {}".format(p, (row,col),self.cache[tile]['raster'][row % mrow][col % mcol]))
			
			return cache[tile]['raster'][row][col]
		finally:
			# locker.release()
			pass

if __name__ == "__main__":

	"validate the elvation model"


	#a = ( -74.0059,40.7128, 50)#nyc
	#b = ( -118.2437,34.0522, 20)#la
	
	# breakiron
	a = (-76.881249, 40.954899)
	
	# house
	b = (-76.897619, 40.955291)
	
	# susquehanna
	#b = (-76.872811, 40.798964, 20)

	#philly
	#b = (-75.1652,39.9526, 50)
	
	#miami
	#b = (-80.1918, 25.7617, 50)

	#psu	
	b = (-77.859340, 40.798571 )
	from geopath import GeoPath	
	import matplotlib.pyplot as plt

	g = GeoPath(a,b, resolution = 300)
	print("a: {}".format(a))
	print('path has {} points'.format(len(g.path)))
	print("b: {}".format(b))
	print("total distance is {} meters".format(g.distance()))

	fig = plt.figure(figsize=(8.5,11))
	ax = plt.subplot(211)



	
	ax.set_title('Elevation Profile')
	ax.plot([g.point_distance(x, a) for x in g.path],
			[x[2] for x in g.path], 's-', color='black', ms=6, lw=2, label="SRTM1")

	#from elevation import Elevation
	e = Elevation()
	ws_pts = [e.lookup_ws(x) for x in g.path]
	ax.plot([g.point_distance(x, a) for x in g.path],
			ws_pts, 'o--', color='black', ms=6, lw=2, label="3DEP")
	ax.set_ylabel('meters')
	ax.set_xlabel('meters from start')
	ax.legend(loc="lower right")


	ax = plt.subplot(212)
	#ax.set_title("Error")
	ax.plot([g.point_distance(x, a) for x in g.path],
			[g.path[i][2] - ws_pts[i] for i in range(len(ws_pts))], 'x-', color='black', ms=6, lw=2, label="Difference")
	ax.set_ylabel('meters')
	ax.set_xlabel('meters from start')
	ax.legend()

	print("average error is: {}".format(numpy.mean([g.path[i][2] - ws_pts[i] for i in range(len(ws_pts))])))


	plt.show()