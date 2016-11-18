
import matplotlib.pyplot as plt
from descartes import PolygonPatch
from processSamplePoints import make_patch, plot_shapes
from pointSampler import PopulationBasedPointSampler
import pymongo
from pprint import pprint
from elevation import Elevation
import numpy
import math
import os.path
import multiprocessing
from county_lookup import state_name

def plot_single_place(outputfmt, placename, cover_by_place_q):
	#ps = PopulationBasedPointSampler()

	connection = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015')
	db = connection.get_default_database()	
	e = Elevation() # to look up point elevations.		

	query = {'name':placename}
		
	cover_by_place = []
	lossbynumbase = {}			
	loss_threshold= {}	
	# qfilter = {'_id':1}
	# if not os.path.exists(outputfmt.format(placename, i, 'elevation')):
	# 	qfilter ['shapes'] = 1
	# 	qfilter ['points'] = 1
	
	# have to talk out the filter for just id to comptue other values.
	cursor = db['POINTS'].find(
					query, 
					{'_id':1, 'LSAD':1, 'state':1, 'points':1, 'shapes':1, 'shape_ids':1}, 
					no_cursor_timeout=True)#.limit(2)
	state = None
	for i, pointdoc in enumerate(cursor):
		state = pointdoc['state']
		print ("{}: {} of {}.".format(placename, i+1, cursor.count()))
		lqry = {'point_docid': pointdoc['_id'], 'tx_height': 5, 'rx_height': 1}
		#lqry = {'point_docid': pointdoc['_id']}
		
		if not os.path.exists(outputfmt.format(placename, i, 'loss')):
			if i == 0:
				for rsltdoc in db['POINTRESULTS'].find(lqry, {'nodes':1, 'num_basestations':1, 'loss_threshold':1}):
					lossbynumbase[rsltdoc['num_basestations']] = [x['min_loss'] for x in rsltdoc['nodes'] if not math.isnan(x['min_loss'])]	
					loss_threshold[rsltdoc['num_basestations']] = [rsltdoc['loss_threshold']]
			else:
				for rsltdoc in db['POINTRESULTS'].find(lqry, {'nodes':1, 'num_basestations':1, 'loss_threshold':1}):
					lossbynumbase[rsltdoc['num_basestations']] += [x['min_loss'] for x in rsltdoc['nodes'] if not math.isnan(x['min_loss'])]
					loss_threshold[rsltdoc['num_basestations']].append(rsltdoc['loss_threshold'])
		
		#cqry = {'point_docid': pointdoc['_id'], 'tx_height': 5, 'rx_height': 1, 'num_basestations': 1}
		cqry = {'point_docid': pointdoc['_id'], 'num_basestations': 1}
		cover_by_place += [x['connected'] for x in db['POINTRESULTS'].find(cqry, {'connected':1})]
		
		#skip the rest, for now.
		#continue 

		#print(lossbynumbase)
		#print(loss_threshold)

		# stats are the same, so only do it once.
		if i == 0:

			if (not os.path.exists(outputfmt.format(placename, i, 'elevation'))) or \
				(not os.path.exists(outputfmt.format(placename, i, 'stats'))):

				fig = plt.figure(figsize = (8,8))
				ax = plt.subplot(111)
				
				
				if pointdoc['LSAD'] == 'County':
					c_shp_query = {'properties.NAME': placename, 'properties.STATE': pointdoc['state']}
					c_shp = list( db['GENZ2010_050'].find(c_shp_query) )

					#plot_shapes(ax, city_shp, filled= True, show_states = True, fc=lambda x:'red', alpha=0.99)
					plot_shapes(ax, c_shp, filled= False, show_states = True)
					
				elif pointdoc['LSAD'] == 'city':
					city_shp_query = {'properties.NAME': placename, 'properties.STATE': pointdoc['state']}		
					city_shp = list( db['GENZ2010_160'].find(city_shp_query) )

					#plot_shapes(ax, city_shp, filled= True, show_states = True, fc=lambda x:'red', alpha=0.99)
					plot_shapes(ax, city_shp, filled= False, show_states = True)
				else:
					print ("WARN: unknown LSAD: {}, not plotting outline".format(pointdoc['LSAD']))


				if 'shapes' not in pointdoc:
					print ("getting shapes...")
					sqry = {'_id': {'$in': pointdoc['shape_ids']}}
					shapes =list(db['GENZ2010_140'].find(sqry))					
				else:
					shapes = pointdoc['shapes']

				
				plot_shapes(ax, shapes, filled=True, show_states=True)

				# this is one way to do it
				# tract_shp = list(ps.get_tract_shapes_in_area(city_shp[0]))
				# plot_shapes(ax, tract_shp, filled= True, show_states = True)		

				
				elev_data = []
				for pt in pointdoc['points']:
					ax.plot(pt['coordinates'][0],pt['coordinates'][1], '.', color='black', ms=4, lw=2, alpha=0.75)
					elev_data.append(e.lookup(pt['coordinates']))

				ax.ticklabel_format(useOffset=False, style="plain")
				
				ax.set_title("{}, {}".format(placename, state_name(state)))
				ax.axis('equal')

				plt.tight_layout()
				plt.savefig(outputfmt.format(placename, i, 'tracts'))
				plt.close(fig)

				# show elevation distribution
				fig = plt.figure(figsize = (8,8))
				ax = plt.subplot(111)
				ax.hist(elev_data, normed=1, fill=False, ec="black", lw=3, hatch=".")
				ax.set_title(placename)
				ax.set_xlabel('Elevation (meters)')
				ax.set_ylabel('Rate')	
				ax.axis('tight')
				plt.savefig(outputfmt.format(placename, i, 'elevation'))
				plt.close(fig)



				print("{} has {} tracts.".format(placename, len(shapes)))
				areas = [sh['properties']['area']['effective'] / (1000.0**2) for sh in shapes if 'area' in sh['properties']] # convert meters to KM
				pops = [sh['properties']['population']['effective']/1000.0 for sh in shapes if 'area' in sh['properties']]

				#print (areas)
				#print (pops)
				print ('total pop: ', sum(pops), 'median: ', numpy.median(pops))
				print ('total area: ', sum(areas), 'median: ', numpy.median(areas))
			

			if not os.path.exists(outputfmt.format(placename, i, 'stats')):

				if areas != None and pops !=None:
					fig = plt.figure(figsize = (8,4))	

					ax = plt.subplot(121)
					ax.hist(areas, normed=0, fill=False, ec='black', lw=3, hatch='/')
					ax.set_title("Area")
					ax.set_xlabel('Square Kilometers')
					ax.set_ylabel('Count')

					ax.axis('normal')

					ax = plt.subplot(122)
					ax.set_title("Population")
					ax.hist(pops, normed=0, fill=False, ec='black', lw=3, hatch='x')
					ax.set_xlabel('Population (Thousands)')
					ax.set_ylabel('Count')

					ax.axis('normal')

					#ax.violinplot ([areas, pops], showmeans=False, showmedians=True)
					#ax.set_xticklabels(['Area', 'Population'])
					
					plt.tight_layout()								
					plt.savefig(outputfmt.format(placename, i, 'stats'))
					plt.close(fig)

	#if not os.path.exists(outputfmt.format(placename, i, 'loss')):
	if 1:
		# show loss distribution
		fig = plt.figure(figsize = (8,4))
		ax = plt.subplot(111)

		bases = sorted(lossbynumbase.keys())

		if len(bases) > 0:
			# print ('plot bases: ', end="")
			# pprint(bases)

			# print ('loss values: ', end="")
			# pprint ([lossbynumbase[bs] for bs in bases])

			ax.violinplot(
				[lossbynumbase[bs] for bs in bases],
				bases,
				showmeans=False, showmedians=True)

			# print('medians are: ', end="")
			# pprint([numpy.median(loss_threshold[i]) for i in bases])

			ax.plot(
				bases, 
				[numpy.median(loss_threshold[i]) for i in bases],
			 	'--', alpha=0.5, color='green', lw=2)
			

			ax.set_title("{}, {}".format(placename, state_name(state)))
			ax.set_xlabel('Number of basestations')
			ax.set_ylabel('Loss (dB)')
			ax.axis('tight')
			plt.tight_layout()
			plt.savefig(outputfmt.format(placename, i, 'loss'))			
			plt.close(fig)
		else:
			print (lossbynumbase)
			print (bases)
	cover_by_place_q.put( (placename, cover_by_place) )

if __name__=="__main__":

	connection = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015')
	db = connection.get_default_database()	

	#placename = "DuBois"
	#placename = "Philadelphia"
	#placename = "Harrisburg"
	#placename = "St. Marys"
	#placename = "Parker"
	cover_by_place = {}
	
	outputfmt = "figures/places/{}_{}_{}.pdf"

	threads = []
	cbpq = multiprocessing.Queue()

	#for placename in db['POINTRESULTS'].distinct('name'):
	#for placename in ["Philadelphia", "St. Marys"]:
	#for placename in ["St. Marys"]:
	for placename in ['Potter']:

		if placename == 'Pennsylvania':
			continue

		t= multiprocessing.Process(target=plot_single_place, name=placename, 
			args=(outputfmt, placename, cbpq))
		t.start()
		threads.append(t)

		if len(threads) > 6:
			print("Waiting for {}".format(threads[0].name))
			threads[0].join()	
			del threads[0]


	for t in threads:
		print("Waiting for {}".format(t.name))
		t.join()
	
	cover_by_place = {}
	while not cbpq.empty():
		pn, cover = cbpq.get()
		if len(cover) > 0:
			cover_by_place[pn] = cover

	print("all threads done.")


	if placename == 'Pennsylvania':
		pprint (cover_by_place)

		# overall loss by all places with one basestation
		fig = plt.figure(figsize = (12,3))
		ax = plt.subplot(111)

		scovers = sorted(cover_by_place.items(), key=lambda x: numpy.median(x[1]))

		#pprint(scovers)
		place, vals = zip(*scovers)
		#pprint(place)
		#pprint(vals)

		med_med = numpy.median([numpy.median(x) for x in vals])

		print("Overall median connectivity is {}".format(med_med))

		ax.violinplot(
			vals,		
			showmedians=True, showmeans=False)

		ax.plot(range(0,2+len(place)), [med_med]*(len(place)+2),
			'--', alpha=0.5, color='green', lw=2)
		ax.set_xticks(range(1,1+len(place)))
		ax.set_xticklabels(place, rotation=75, ha='right')
		ax.set_ylabel("Coverage (rate)")
		ax.set_title("Coverage from one base station")
		ax.axis('tight')
		plt.tight_layout()
		plt.savefig(outputfmt.format('overall', 'PA', 'connection'))			
		plt.close(fig)



		