
import pymongo
import gridfs
db = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015').get_default_database()
col = db['SRTMGL1']

gfs = gridfs.GridFS(db)


allfiles = gfs.find()

for f in allfiles:
	print('Remove {} ({})'
		.format(f.filename,f._id))
	gfs.delete(f._id)
