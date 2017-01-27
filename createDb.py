"""MongoDB can perform spatial queries on GeoJSON objects,
create the database by importing the census tract shapefiles.

"""
import glob
import fiona
import pymongo
from pprint import pprint
#import struct
import traceback

importCensusData = False
import20m = True
if import20m:
	db = pymongo.MongoClient('mongodb://owner:1M$t5iOqXzWMw&aM@eg-mongodb.bucknell.edu/planit').get_default_database()
	col = db['GENZ2010_050_20m']
	col.create_index([("geometry", pymongo.GEOSPHERE)])

	for shfile in glob.glob('GENZ2010/gz_2010_us_050_00_20m.shp'):
		print("Reading: {}".format(shfile))
		with fiona.open(shfile) as fc:
			for shp in fc:
				col.insert_one(shp)
				print(".", end="")


if 0:
	#remove dupes from duble import
	db = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015').get_default_database()
	col = db['GENZ2010_040']

	for geoid in col.distinct("properties.GEO_ID"):
		print ("checking ", geoid)

		dupes = col.find({"properties.GEO_ID": geoid}, {'_id':1, 'properties':1})
		if dupes.count() > 1:
			d = list(dupes)
			print("keep ", d[0])

			print("remove ", d[1:])
			col.remove({"_id": {'$in': [x['_id'] for x in d[1:]]}})


if importCensusData:
	# see https://www.census.gov/geo/maps-data/data/summary_level.html for levels

	if 0:  # 140 (staty-county-census tract ) is already imported
		db = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015').get_default_database()
		col = db['GENZ2010_140']
		col.create_index([("geometry", pymongo.GEOSPHERE)])

		for shfile in glob.glob('GENZ2010/gz_2010_*_140_00_500k.shp'):
		#for shfile in ['GENZ2010/gz_2010_42_140_00_500k.shp']: #import PA
			if 'GENZ2010/gz_2010_42_140_00_500k.shp' in shfile:
				continue
			print("Reading: {}".format(shfile))
			with fiona.open(shfile) as fc:
				for shp in fc:
					col.insert_one(shp)
					print(".", end="")

	if 0:
		# import 160, state-place data
		db = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015').get_default_database()
		col = db['GENZ2010_160']
		col.create_index([("geometry", pymongo.GEOSPHERE)])

		for shfile in glob.glob('GENZ2010/gz_2010_*_160_00_500k.shp'):
			print("Reading: {}".format(shfile))
			with fiona.open(shfile) as fc:
				for shp in fc:
					col.insert_one(shp)
					print(".", end="")

	if 0:
		# import US 050, state-county data for entire USA
		db = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015').get_default_database()
		col = db['GENZ2010_050']
		col.create_index([("geometry", pymongo.GEOSPHERE)])

		for shfile in glob.glob('GENZ2010/gz_2010_*_050_00_500k.shp'):
			print("Reading: {}".format(shfile))
			with fiona.open(shfile) as fc:
				for shp in fc:
					col.insert_one(shp)
					print(".", end="", flush=True)

	if 0:
		#import state outlines
		#GENZ2010/gz_2010_us_040_00_500k.shp
		db = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015').get_default_database()
		col = db['GENZ2010_040']
		col.create_index([("geometry", pymongo.GEOSPHERE)])

		for shfile in glob.glob('GENZ2010/gz_2010_us_040_00_500k.shp'):
			print("Reading: {}".format(shfile))
			with fiona.open(shfile) as fc:
				for shp in fc:
					col.insert_one(shp)
					print("add {}".format(shp['properties']['NAME']))

importElevationData = False

if importElevationData:

	#from util.hgt import HGTFile
	import zipfile
	from osgeo import gdal
	import osgeo.gdalconst as gdalconst
	import tempfile
	import os.path
	import os
	# geojson and mongodb don't work together
	#from geojson import Feature, Polygon
	#import geojson
	import gridfs
	from bson import json_util
	from affine import Affine

	# Enable GDAL/OGR exceptions
	gdal.UseExceptions()

	db = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015').get_default_database()
	col = db['SRTMGL1']
	col.create_index([("geometry", pymongo.GEOSPHERE)])
	gfs = gridfs.GridFS(db)

	i = 0
	hgt_info={1201*1201*2: 1201,
			  3601*3601*2: 3601}

	for hgtfile in sorted(glob.glob('../../SRTMGL1/*.zip')):
	#for hgtfile in ['../../SRTMGL1/N40W076.SRTMGL1.hgt.zip']:
		print("opening: {}".format(hgtfile))

		bn = os.path.basename(hgtfile)
		if bn[0] != 'N':
			continue
		if bn[3] != 'W':
			continue

		with zipfile.ZipFile(hgtfile, 'r') as z:

			for zipcontent in z.namelist():
				# check if this doc exists in mongodb
				dbdoc = col.find_one({"type":"Feature", "properties.SrcFile": zipcontent})

				if dbdoc == None:
					data = z.read(zipcontent)
					tmphgtfile = os.path.join(tempfile.gettempdir(), zipcontent)
					try:
						with open(tmphgtfile, 'wb') as wf:
							wf.write(data)

						print('unzipped to: {}'.format(tmphgtfile))

						gfsdoc = gfs.find_one({'filename': zipcontent})
						if gfsdoc == None:
							print('uploading to gridfs...')
							# upload to GridFS
							gfs_id = gfs.put(data, filename=zipcontent, contentType='application/octet-stream')
							print('got gfs_id: {}'.format(gfs_id))
						else:
							print('file {} already has id: {}'.format(zipcontent, gfsdoc._id))
							gfs_id = gfsdoc._id

						try:
							d = gdal.Open(tmphgtfile, gdalconst.GA_ReadOnly)
							gt = d.GetGeoTransform()
							r1 = d.GetRasterBand(1)
						except:
							traceback.print_exc()
							continue

						def lim(lng,lat):
							if lng < -180:
								lng = -180
							if lng > 180:
								lng = 180
							return lng,lat

						# create the poly that bounds this raster
						# ref: http://www.gdal.org/classGDALDataset.html#a5101119705f5fa2bc1344ab26f66fd1d

						# fix with inverse affine with points 0,0, 0,3600, 3600,3600
						poly = (
									(
										lim(gt[0], gt[3]),						# top left
										lim(gt[0]+d.RasterXSize*gt[1], gt[3]),	# top right
										lim(gt[0]+d.RasterXSize*gt[1]+d.RasterYSize*gt[2], gt[3]+d.RasterXSize*gt[4]+d.RasterYSize*gt[5]), # bottom right
										lim(gt[0]+d.RasterYSize*gt[2], gt[3]+d.RasterXSize*gt[4]+d.RasterYSize*gt[5]), # bottom left
										lim(gt[0], gt[3])
									)
								)
						#polygeo = geojson.dumps(poly, sort_keys=True)

						#raster = r1.ReadAsArray(0,0, d.RasterXSize, d.RasterYSize)

						#raster = r1.ReadRaster(0,0,d.RasterXSize, d.RasterYSize,
						#	d.RasterXSize, d.RasterYSize, gdalconst.GDT_Int16)
						rmin,rmax,rmean,rstdev = r1.GetStatistics(True, True)
						doc = {	'type': 'Feature',
								'geometry': {'type': 'Polygon', 'coordinates': [poly]},
								'properties':{
											"SrcFile": zipcontent,
											"TileName": os.path.splitext(zipcontent)[0],
											"GeoTransform": gt,
											"Unit type": r1.GetUnitType(),
											"Min": rmin,
											"Max": rmax,
											"Mean": rmean,
											"StdDev": rstdev,
											"RasterFile": gfs_id
									}
								}

						print (json_util.dumps(doc,sort_keys=True))
						col.insert_one(doc)
					finally:
						if os.path.exists(tmphgtfile):
							os.remove(tmphgtfile)
				else:
					print("{} is already in db!: {}".format(zipcontent, dbdoc['_id']))



		# 		size = 0
		# 		if len(data) in hgt_info:
		# 			size = hgt_info[len(data)]

		# 		i = 0
		# 		fmt = ">" + ("h" * size)
		# 		d = []
		# 		while i < size:
		# 			values = struct.unpack(fmt, data[i:i+size*2])
		# 			d.append(values)
		# 			i += 1


		i+=1

	print(i)
