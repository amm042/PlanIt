

import numpy as np

from pyproj import Geod, Proj, transform

import matplotlib.pyplot as plt
from matplotlib.ticker import NullLocator
from scipy.interpolate import interp2d, griddata

from descartes import PolygonPatch

from shapely.geometry import shape, mapping
from county_lookup import state_name, county_name

import pymongo

from pykml.factory import KML_ElementMaker as KML
from lxml import etree
import datetime
from pprint import pprint
import os.path
import random

from bson import ObjectId
from types import SimpleNamespace
def plot_contours(area, points, fig, ax, plot_legend= True, plot_points= True,
	threshold = 180):

	geod = Geod(ellps='WGS84')

	xmin,ymax,xmax,ymin = area.bounds

	x,y,z  = zip(*points)
	X,Y = np.mgrid[xmin:xmax:((xmax-xmin)/250), ymin:ymax:((ymax-ymin)/250)]
	Z = griddata( (x,y), z, (X,Y), method='cubic')
	#Z = griddata( (x,y), z, (X,Y), method='linear')

	mindb = threshold-100
	maxdb = threshold
	N = int((maxdb - mindb) / 10)
	v = np.linspace(mindb, maxdb, N+1)

	# replace anything less than mindb with mindb (leaving max/NaN alone)
	#print(Z)
	#np.maximum(Z, mindb, out=Z)
	#print("-"*80)
	#print(Z)
	#np.clip(Z, mindb, maxdb, out=Z)

	#CS = ax.contour(X,Y,Z,N, linewidth=0.5, colors='k', alpha=0.3)
	CSF = ax.contourf(X,Y,Z,N, cmap=plt.cm.RdYlGn_r, alpha=1,
		vmin = v[0], vmax=v[-1], levels=v, extend='min')
		#vmin = min([p[2] for p in points]), vmax=max([p[2] for p in points]))

	if plot_legend:
		cb = fig.colorbar(CSF,ticks =v)
		cb.set_label("dB Loss")

	if plot_points:
		for p in points:
			#print (p)
			ax.plot(p[0], p[1], '.', color='k', ms=2, alpha=0.6)

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

def plot_shapes(ax, shapes, filled = False, show_states = False):
	# have to buffer the results to see how many colors to generate

	if filled:
		color_list = plt.cm.Dark2(np.linspace(0, 1, len(shapes)))
		fc = lambda x: color_list[x]
	else:
		fc = lambda x: 'none'

	states = set()
	geoid = {}
	# get the shapes covered by the coverage area.
	for i, shp in enumerate(shapes):
		p = shp['properties']

		#track states we hit
		if p['STATE'] not in states:
			states.add(p['STATE'])
		# also store the goeid so we dont plot again later
		geoid[p['GEO_ID']] = shp

		if p['LSAD'] == 'Tract':
			label = "{} {} [{}]".format(state_name(p['STATE']),
						county_name(p['STATE'],p['COUNTY']), p['TRACT'])
		else:
			label = p['NAME']

		#print ("-"*10 + label + "-"*10)
		#pprint(p['population'])


		ec = 'black'
		lw = 1

		if 'population' in p:
			if p['population']['effective'] < 0.01:
				ec = 'blue'
				lw = 2
									#was fc = color_list[i],

		patches = make_patch(shp['geometry'], fc=fc(i), lw=lw, ec=ec, label=label, alpha=0.16)
		for p in patches:
			ax.add_patch(p)

def PlotContours(resdocs, bounds, threshold, out_path, fname):
	if not os.path.exists(out_path):
		os.makedirs(out_path)
	outputfile = os.path.join(out_path, fname + ".png")
	if os.path.exists(outputfile):
		logging.info("Skip loss {} exists".format(outputfile))
		return outputfile

	fig = plt.figure()	#figsize = (12,8)
	#ax = plt.Axes(fig=fig, rect=[0, 0, 1, 1], facecolor='blue')
	#ax = plt.subplot(111)
	ax = fig.add_subplot(111, facecolor=None)
	ax.set_axis_off()
	ax.set_frame_on(False)
	ax.autoscale(False)

	b =SimpleNamespace()
	b.bounds = (bounds['west'], bounds['north'], bounds['east'], bounds['south'])


	xmin,ymax,xmax,ymin = b.bounds
	ax.set_xlim((xmin, xmax))
	ax.set_ylim((ymin, ymax))
	ax.margins(0,0)
	ax.xaxis.set_major_locator(NullLocator())
	ax.yaxis.set_major_locator(NullLocator())

	points = {}
	for doc in resdocs:
		for k in ['nodes', 'grid']:
			for x in doc[k]:
				l = (x['point']['geometry']['coordinates'][0],
					 x['point']['geometry']['coordinates'][1])
				if l in points:
					points[l] += [x['min_loss']]
				else:
					points[l] = [x['min_loss']]

	points = [(k[0], k[1], float(np.mean(v))) for k,v in points.items() ]

	plot_contours(
		b,
		points,
		fig,
		ax,
		threshold = threshold,
		plot_legend=False, plot_points=True)

	fig.subplots_adjust(top=1,bottom=0,right=1,left=0,hspace=0,wspace=0)
	fig.savefig(outputfile, dpi=300, transparent=True,
		bbox_inches="tight", pad_inches=0.0, frameon=False)
	return outputfile

def PlotLoss(resdocs, threshold, out_path, fname):
	if not os.path.exists(out_path):
		os.makedirs(out_path)
	outputfile = os.path.join(out_path, fname + ".pdf")
	if os.path.exists(outputfile):
		logging.info("Skip loss {} exists".format(outputfile))
		return outputfile

	loss = {}
	for doc in resdocs:
		if doc['num_basestations'] in loss:
			loss[doc['num_basestations']] += [x['min_loss'] for x in doc['nodes']]
		else:
			loss[doc['num_basestations']] = [x['min_loss'] for x in doc['nodes']]

	fig = plt.figure(figsize = (8,8))
	ax = plt.subplot(111)
	kys = sorted(loss.keys())
	ax.violinplot(
		[loss[k] for k in kys],
		kys,
		showmeans=False, showmedians=True)
	ax.plot( (kys[0]-1, kys[-1]+1), (threshold, threshold),
		'--', lw=2, color='blue')
	#ax.set_title(cityname)
	ax.set_ylabel("Loss (dBm)")
	ax.set_xlabel("Number of basestations")

	#ax.set_ylim((0.8, 1))
	ax.axis('tight')

	plt.savefig(outputfile, dpi=300)
	return outputfile

def PlotCoverage(resdocs, out_path, fname):
	if not os.path.exists(out_path):
		os.makedirs(out_path)
	outputfile = os.path.join(out_path, fname + ".pdf")

	if os.path.exists(outputfile):
		logging.info("Skip coverage {} exists".format(outputfile))
		return outputfile

	coverage_rate = {}

	for doc in resdocs:
		if doc['num_basestations'] in coverage_rate:
			coverage_rate[doc['num_basestations']].append(doc['connected'])
		else:
			coverage_rate[doc['num_basestations']] = [doc['connected']]

	fig = plt.figure(figsize = (8,8))
	ax = plt.subplot(111)
	kys = sorted(coverage_rate.keys())
	ax.violinplot(
		[coverage_rate[k] for k in kys],
		kys,
		showmeans=False, showmedians=True)

	#ax.set_title(cityname)
	ax.set_ylabel("Connected (rate)")
	ax.set_xlabel("Number of basestations")

	#ax.set_ylim((0.8, 1))
	ax.axis('tight')

	plt.savefig(outputfile, dpi=300)
	return outputfile

if __name__ == "__main__":


	connection = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015')
	db = connection.get_default_database()


	#cityname = 'Butler'
	#result = db['POINTRESULTS'].find({'name': cityname})
	#print("{} has {} results.".format(cityname, result.count())

	#for cityname in db['POINTRESULTS'].distinct('name'):
	#for cityname in ['Philadelphia']:
	#for cityname in ['Pennsylvania']:
	for cityname in ['Potter']:
		# if cityname in ["Shamokin", "Uniontown", "Bethlehem", "Bradford", "Chester", "Clairton",
		# "Coatesville", "Connellsville", "DuBois", "Duquesne", "Easton", "Erie", "Aliquippa", "Allentown", "Altoona",
		# "Beaver Falls", "Farrell", "Arnold", "Franklin", "Jeannette", "Johnstown", "Lebanon", "Lock Haven",
		# "Lower Burrell", "Latrobe", "Greensburg", "Harrisburg", "Hazleton", "Hermitage", "McKeesport", "Meadville",
		# "Monongahela", "Pittsburgh", "Pittston", "Oil City", "Reading", "Pottsville", "Sunbury", "Titusville",
		# "St. Marys", "Scranton", "Warren", "Washington", "Wilkes-Barre", "Williamsport", "York", "Nanticoke",
		# "New Castle", "New Kensington", "Sharon"]:

			outputfile = "figures/"+cityname+"_coverage.pdf"

			#if os.path.exists(outputfile):
			#	print("Skip {}, {} exists".format(cityname, outputfile))
			#	continue

			print("processing {}".format(cityname))

			basestations = db['POINTRESULTS'].find({'name': cityname, 'tx_height': 5, 'rx_height': 1}).distinct('num_basestations')

			coverage_rate = {}
			for b in basestations:
				res = db['POINTRESULTS'].find({'name': cityname, 'tx_height': 5, 'rx_height': 1, 'num_basestations': b})

				for result in res:
					print("{} ({}) has coverage {} with {} basestation(s)".format(
						result['_id'],
						cityname,
						result['connected'],
						b))
					if b in coverage_rate:
						coverage_rate[b].append(result['connected'])
					else:
						coverage_rate[b] = [result['connected']]

			# pprint (coverage_rate)
			# print("vals = ", end="")
			# pprint(list(coverage_rate.values()))
			# print("keys = ", end="")
			# pprint(coverage_rate.keys())


			fig = plt.figure(figsize = (8,8))
			ax = plt.subplot(111)
			kys = sorted(coverage_rate.keys())
			ax.violinplot(
				[coverage_rate[k] for k in kys],
				kys,
				showmeans=False, showmedians=True)

			ax.set_title(cityname)
			ax.set_ylabel("Connected (rate)")
			ax.set_xlabel("Number of basestations")

			#ax.set_ylim((0.8, 1))
			ax.axis('tight')

			#plt.show()
			plt.savefig("figures/"+cityname+"_coverage.pdf", dpi=300)
		# else:
		# 	print("SKIP {}".format(cityname))
