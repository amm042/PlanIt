"use ITWOM and SRTM elvation data to compute link loss between to points"
import math
from geopath import GeoPath
import matplotlib.pyplot as plt	

from itwom import loss_along_path

def feet_to_meters(x):
	return x*0.3048

if __name__=="__main__":
	# last value is elevation above ground level for antenna
	
	#a = ( -74.0059,40.7128, 50)#nyc
	#b = ( -118.2437,34.0522, 20)#la
	
	# breakiron
	a = (-76.881249, 40.954899)
	
	# house
	#b = (-76.897619, 40.955291)
	
	# susquehanna
	#b = (-76.872811, 40.798964, 20)

	#philly
	#b = (-75.1652,39.9526, 50)
	
	#miami
	#b = (-80.1918, 25.7617, 50)

	#psu
	
	b = (-77.859340, 40.798571 )
	
	g = GeoPath(a,b, resolution = 300)
	print("a: {}".format(a))
	print('path has {} points'.format(len(g.path)))
	print("b: {}".format(b))
	print("total distance is {} meters".format(g.distance()))

	fig = plt.figure(figsize=(8.5,11))
	ax = plt.subplot(311)

	ax.get_xaxis().get_major_formatter().set_scientific(False)
	ax.get_yaxis().get_major_formatter().set_scientific(False)

	ax.set_title('Path overview')

	ax.plot([i[0] for i in g.path],
			[i[1] for i in g.path], 'v--', alpha=0.5, color='green', lw=2)

	ax.plot(a[0], a[1], 'x', color='red')
	ax.plot(b[0], b[1], 'o', color='blue')

	
	#ax.axis('equal')


	ax = plt.subplot(312)
	ax.set_title('Elevation Profile')
	ax.plot([g.point_distance(x, a) for x in g.path],
			[x[2] for x in g.path], 's-', color='blue', ms=12, lw=2)

	#from elevation import Elevation
	#e = Elevation()
	#ax.plot([g.point_distance(x, a) for x in g.path],
			#[e.lookup_ws(x) for x in g.path], 'o-', color='red', ms=12, lw=2)

	ax = plt.subplot(313,sharex=ax)
	ax.set_title('Path loss')

	loss = loss_along_path(feet_to_meters(50), feet_to_meters(30), g)
	ax.plot([g.point_distance(x, a) for x in g.path],
			loss, '.-', color='green', ms=12, lw=2)
	ax.set_ylim(bottom=80)
	#ax.axis('tight')
	#plt.subplots_adjust(hspace=0.40)
	plt.tight_layout()
	plt.show()

	#ll = LinkLoss()


	#ll.p2p(tx = brki, rx = home, freq = 900e6)