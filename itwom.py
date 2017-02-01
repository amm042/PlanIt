"wrapper for swig generaetd pyitwom3 wrapper that is easier to use"

import pyitwom3

from geopath import GeoPath


class ItwomParams():
	def __init__(self, **kwargs):
		# setup default values
		self.eps_dielect = 15;
		self.sgm_conductivity = 0.005
		self.eno_ns_surfref = 301.0
		self.freq_mhz = 900
		self.radio_climate = 5
		self.pol = 0 # 0=horiz 1=vert 2=circ
		self.conf = 0.5
		self.rel = 0.5

		# override anything provided in kwargs
		for k,v in kwargs.items():
			setattr(self,k,v)

def itwomParams_city(freq_mhz = 900):
	return ItwomParams(freq_mhz = freq_mhz, eps_dielect = 5, sgm_conductivity = 0.001)
def itwomParams_average(freq_mhz = 900):
	return ItwomParams(freq_mhz = freq_mhz, eps_dielect = 15, sgm_conductivity = 0.005)

def point_loss(	tx_latlon, tx_height,
				rx_latlon, rx_height,
				resolution=30,
				params=itwomParams_average(),
				elev= None):
	"""return the loss between two points

	A great circle path is constructed between the tx and rx points

	resolution -- is the resolution for path generation in meters
	params -- is a ItowmParams class object (or use the default)
	"""
	# print(tx_latlon, tx_height)
	# print(rx_latlon, rx_height)
	p = GeoPath(tx_latlon, rx_latlon, resolution=resolution, elev=elev)
	return loss_along_path(tx_height, rx_height, p, params=params, evaluate_path=False)


def loss_along_path(tx_height, rx_height, p, params=itwomParams_average(), evaluate_path=True):
	"""return the loss along path p using the itwom params

	p -- is a GeoPath class object
	params -- is a ItowmParams class object (or use the default)
	evaluate_path -- if true the loss at all points on the path are computed, else
	  just compute the path loss at the final point in the path.
	Note we assume the points are equally spaced along the path"""

	# allocate the height array across the entire path
	elev = pyitwom3.doubleArray(2+len(p.path))
	elev[0] = len(p.path)-1 # numpoints -1
	elev[1] = p.distance() / elev[0] # distance between samples in meters

	edata = [pt[2] for pt in p.path]

	# itwom doesn't like negative elevations, shift everything up.
	minel = min(edata)
	if minel < 0:
		offset= abs(minel)
		for i in range (len(edata)):
			edata[i]+=offset

	for i,pt in enumerate(edata):
		#print(i,pt)
		elev[2+i] = float(pt) # elevation data

	errnum = pyitwom3.intp()
	loss = pyitwom3.doublep()

	if evaluate_path:
		rslt = [0] # 0 db loss at source
		for i in range(1,len(p.path)):
			elev[0] = i

			# print("point_to_point: ")
			# for q in range(2+len(p.path)):
			# 	print(elev[q], ", ", end="")
			# print()

			strmode = pyitwom3.point_to_point(elev, tx_height, rx_height,
				params.eps_dielect,
				params.sgm_conductivity,
				params.eno_ns_surfref,
				params.freq_mhz,
				params.radio_climate,
				params.pol,
				params.conf,
				params.rel,
				loss, errnum)
			# print("{:3d}: loss= {}, errnum={}, strmode={}".format(
			# 	i,
			# 	pyitwom3.doublep.value(loss),
			# 	pyitwom3.intp.value(errnum),
			# 	strmode))
			rslt.append(pyitwom3.doublep.value(loss))
		return rslt
	else:
		# print("point_to_point: ")
		# for q in range(2+len(p.path)):
		# 	print(elev[q], ", ", end="")
		# print()



		strmode = pyitwom3.point_to_point(elev, tx_height, rx_height,
			params.eps_dielect,
			params.sgm_conductivity,
			params.eno_ns_surfref,
			params.freq_mhz,
			params.radio_climate,
			params.pol,
			params.conf,
			params.rel,
			loss, errnum)

		return pyitwom3.doublep.value(loss), strmode
