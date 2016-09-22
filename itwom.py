"wrapper for swig generaetd pyitwom3 wrapper that is easier to use"

import pyitwom3


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

def loss_along_path(tx_height, rx_height, p, params=ItwomParams()):
	"""return the loss along path p using the itwom params

	p -- is a GeoPath class object
	params -- is a ItowmParams class object (or use the default)
	Note we assume the points are equally spaced along the path"""

	# allocate the height array across the entire path
	elev = pyitwom3.doubleArray(2+len(p.path))
	elev[0] = len(p.path)-1 # numpoints -1
	elev[1] = p.distance() / elev[0] # distance between samples in meters
	for i,pt in enumerate(p.path):
		print(i,pt)
		elev[2+i] = float(pt[2]) # elevation data

	errnum = pyitwom3.intp()
	loss = pyitwom3.doublep()

	rslt = [0] # 0 db loss at source
	for i in range(1,len(p.path)):
		elev[0] = i

		for q in range(2+len(p.path)):
			print(elev[q], ", ", end="")
		print()

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
		print("{:3d}: loss= {}, errnum={}, strmode={}".format(
			i, 
			pyitwom3.doublep.value(loss),
			pyitwom3.intp.value(errnum),
			strmode))
		rslt.append(pyitwom3.doublep.value(loss))
	return rslt