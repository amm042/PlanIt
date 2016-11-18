import matplotlib.pyplot as plt
import fiona
from descartes import PolygonPatch
from pprint import pprint

from shapely.geometry import shape, mapping, LineString, Polygon
import glob



fig = plt.figure()
ax = fig.gca()


#from geojson import Polygon
import geojson
	
pdump = """{"coordinates": [[90.99986111111112, 27.000138888888888], 
[92.0001388888889, 27.000138888888888], [92.0001388888889, 25.99986111111111], 
[90.99986111111112, 25.99986111111111], [90.99986111111112, 27.000138888888888]], "type": "Polygon"}"""

p = geojson.loads(pdump)

print(p)

# have to conver the geoJSON polygon to a Shapely Polgyon, wich descartes can deal with
ax.add_patch(PolygonPatch(Polygon(p['coordinates']), fc='blue', ec='black', lw=2))

if 1:
	for shfile in ['GENZ2010/gz_2010_us_outline_500k.shp']:
		with fiona.open(shfile) as fc:

			for shp in fc:

				pprint(shp['properties'])
							
				if shp['geometry']['type'] == 'Polygon':
					geo = PolygonPatch(shp['geometry'])
					ax.add_patch(geo)
					
				elif shp['geometry']['type'] == 'MultiPolygon':				
					for poly in shape(shp['geometry']):					
						ax.add_patch(PolygonPatch(poly))

				elif shp['geometry']['type'] == 'LineString':				
					line = LineString(shp['geometry']['coordinates'])
					x,y= line.xy
					ax.plot(x,y, lw=1, color='black')

				else:
					raise Exception("unsupportd geometry")
			



ax.axis('scaled')
plt.show()

