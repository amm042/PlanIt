
import glob
import fiona
from pprint import pprint
import matplotlib.pyplot as plt
from descartes import PolygonPatch
from computeCoverage import plot_shapes
from shapely.geometry import shape

from pointSampler import PopulationBasedPointSampler
import random

def make_patch(geo, **kwargs):
	"takes a geoJSON geometry and returns something matplotlib understands"
	if geo['type'] == 'Polygon':
		return [PolygonPatch(geo,**kwargs)]
		
	elif geo['type'] == 'MultiPolygon':
		p = []
		for poly in shape(geo):
			p.append(PolygonPatch(poly, **kwargs))
			
		return p
	else:
		pprint(geo)
		raise Exception("unsupported geometry")	

fig = plt.figure(figsize = (8,8), dpi=300)
ax = plt.subplot(111)			

for shfile in glob.glob('GENZ2010/gz_2010_42_160_00_500k.shp'):	
	with fiona.open(shfile) as fc:
		shapes=list(fc)


cities = sorted(filter(lambda s: s['properties']['LSAD'] == 'city', shapes), key=lambda s: s['properties']['CENSUSAREA'])


print("{} cities".format(len(cities)))
print(["{} ({})".format(c['properties']['NAME'], c['properties']['CENSUSAREA']) for c in cities])


ipt = list(filter(lambda s: s['properties']['NAME'] == 'Williamsport', cities))

pbps = PopulationBasedPointSampler("ca22eb30af97c6b471419d7fe22b9ce9a5d1fe8d")	

pprint(list(shape(ipt[0]['geometry']).exterior.coords))

# ipt is the geojson dict, convert to a shapely shape object so we can compute the intersection
tracts = list(pbps.get_tract_shapes_in_area(shape(ipt[0]['geometry'])))


plot_shapes(ax, ipt)

plot_shapes(ax, tracts, filled=True)

ax.axis('equal')
plt.show()