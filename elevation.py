
import numpy

from osgeo import gdal
import osgeo.gdalconst as gdalconst
from affine import Affine

import requests
import os.path

import pymongo
import gridfs

import math

class Elevation():
	""" Find the elevation of a given lat/lon location on earth using SRTM data
		
		srtm_path -- the local path to cache STRM tiles
		mongo_str -- connection string to mongodb server / gridfs containing the STRM tiles.
	"""

	def __init__(self, strm_path="./SRTM", mongo_str="mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015"):
		self.db = pymongo.MongoClient(mongo_str).get_default_database()
		self.strm = self.db['STRMGL1']
		self.strm_path = strm_path
		self.gfs = gridfs.GridFS(self.db)

		if not os.path.exists(strm_path):
			os.makedirs(strm_path)
		self.cache = {}

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
		for retries in range(10):
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

	def lookup(self, p):
		"return elevation for point p (lon,lat)"
		#print("lookup for {}".format(p))

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
		
		# load into memory cache
		if not tile in self.cache:			
			local_tilefile = os.path.join(self.strm_path, tile)
			if not os.path.exists(local_tilefile):	
				print("need tile: {} from gridfs".format(tile))
				fp = self.gfs.find_one({'filename':tile})
				if fp == None:
					print("Warning tile {} not found on gridfs, assuming sea level (zeros)".format(tile))
				else:
					print("getting {} bytes from {} to {}.".format(fp.length, fp, local_tilefile))							
					with open(local_tilefile, 'wb') as lfp:
						lfp.write(fp.read())
			
			if os.path.exists(local_tilefile):
				# load from disk to memory cache
				print("loading tile: {}".format(local_tilefile))
				d = gdal.Open(local_tilefile, gdalconst.GA_ReadOnly)
				r1 = d.GetRasterBand(1)
				self.cache[tile] = {
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
				self.cache[tile] = {
					'rows': 3601,
					'cols': 3601,
					'transform': Affine.identity(), # doesn't really matter
					'raster': numpy.zeros((3601, 3601))
				}
		
		row,col = self.geoToCoord((p[0],p[1]), self.cache[tile]['transform'])
		
		#print("transform = {}".format(self.cache[tile]['transform']))
		# mrow = self.cache[tile]['rows']
		# mcol = self.cache[tile]['cols']
		# print("{} == {} has elev {}".format(p, (row,col),self.cache[tile]['raster'][row % mrow][col % mcol]))
		
		return self.cache[tile]['raster'][row][col]