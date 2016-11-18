import matplotlib.pyplot as plt
import fiona
from descartes import PolygonPatch
from pprint import pprint

from shapely.geometry import shape, mapping
import glob



fig = plt.figure()
ax = fig.gca()

count  = 0

for shfile in glob.glob('GENZ2010/gz_2010_us_040_00_500k.shp'):
	with fiona.open(shfile) as fc:



		for shp in fc:

			count += 1
			pprint(shp)
			
			
			if shp['geometry']['type'] == 'Polygon':
				geo = PolygonPatch(shp['geometry'])
				ax.add_patch(geo)
			elif shp['geometry']['type'] == 'MultiPolygon':
				for poly in shape(shp['geometry']):					
					ax.add_patch(PolygonPatch(poly))
			else:
				pprint(shape)
				exit()


print ('count is ', count)

# ax.axis('scaled')
# plt.show()

