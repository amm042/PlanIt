
import matplotlib.pyplot as plt
from descartes import PolygonPatch
from processSamplePoints import make_patch, plot_shapes
from pointSampler import PopulationBasedPointSampler
import pymongo
from pprint import pprint
from elevation import Elevation
import numpy
import math

if __name__=="__main__":

	connection = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015')
	db = connection.get_default_database()	

	
	#for statename in db['POINTRESULTS'].distinct('name'):
	for statename in ["Pennsylvania"]:

		outputfmt = "figures/states/{}_{}_{}.pdf"

		ps = PopulationBasedPointSampler()

		query = {'properties.NAME': statename}
		
		state_shape = list( db['GENZ2010_040'].find(query) )

		query = {'state': '42', 'name':statename}
		
		e = Elevation() # to look up point elevations.


		plot_tracts = False
		plot_elev = False

		lossbynumbase = {}		
		loss_threshold= {}	
		cursor = db['POINTS'].find(query)
		print ("have {} points to process.".format(cursor.count()))
		for i, pointdoc in enumerate(cursor):
			print ("{}: {} of {}.".format(statename, i, cursor.count()))
			lqry = {'point_docid': pointdoc['_id']}

			if i == 0:
				for rsltdoc in db['POINTRESULTS'].find(lqry):
					lossbynumbase[rsltdoc['num_basestations']] = [x['min_loss'] for x in rsltdoc['nodes'] if not math.isnan(x['min_loss'])]	
					loss_threshold[rsltdoc['num_basestations']] = [rsltdoc['loss_threshold']]
			else:
				for rsltdoc in db['POINTRESULTS'].find(lqry):
					lossbynumbase[rsltdoc['num_basestations']] += [x['min_loss'] for x in rsltdoc['nodes'] if not math.isnan(x['min_loss'])]
					loss_threshold[rsltdoc['num_basestations']].append(rsltdoc['loss_threshold'])

			#print(lossbynumbase)
			#print(loss_threshold)

			# stats are the same, so only do it once.
			if i == 0:

				fig = plt.figure(figsize = (8,6))
				ax = plt.subplot(111)

				#plot_shapes(ax, state_shape, filled= True, show_states = True, fc=lambda x:'red', alpha=0.99)
				plot_shapes(ax, state_shape, filled= False, show_states = True)

				if plot_tracts:
					shapes_cur = (db['GENZ2010_140'].find({'_id': {'$in': pointdoc['shape_ids']}}))							
					print("fetching {} tract shapes.".format(shapes_cur.count()))
					shapes = list(shapes_cur)
					plot_shapes(ax, shapes, filled=True, show_states=True)

				# this is one way to do it
				# tract_shp = list(ps.get_tract_shapes_in_area(state_shape[0]))
				# plot_shapes(ax, tract_shp, filled= True, show_states = True)		

							
				for pt in pointdoc['points']:
					ax.plot(pt['coordinates'][0],pt['coordinates'][1], '.', color='black', ms=1, lw=2, alpha=0.75)
					
				ax.ticklabel_format(useOffset=False, style="plain")
				ax.set_title(statename)
				ax.axis('equal')

				plt.tight_layout()
				plt.savefig(outputfmt.format(statename, i, 'tracts'))
				plt.close(fig)

				if plot_elev:	
					elev_data = []			
					for pt in pointdoc['points']:						
						elev_data.append(e.lookup(pt['coordinates']))
					# show elevation distribution
					fig = plt.figure(figsize = (8,8))
					ax = plt.subplot(111)
					ax.hist(elev_data, normed=1, fill=False, ec="black", lw=3, hatch=".")
					ax.set_title(statename)
					ax.set_xlabel('Elevation (meters)')
					ax.set_ylabel('Rate')	
					ax.axis('tight')
					plt.savefig(outputfmt.format(statename, i, 'elevation'))
					plt.close(fig)

				## cant do this at the state level, these stats were included in the shapes within the points, but too much data
				# print("{} has {} tracts.".format(statename, len(shapes)))
				# areas = [sh['properties']['area']['effective'] / (1000.0**2) for sh in shapes] # convert meters to KM
				# pops = [sh['properties']['population']['effective']/1000.0 for sh in shapes]

				# #print (areas)
				# #print (pops)
				# print ('total pop: ', sum(pops), 'median: ', numpy.median(pops))
				# print ('total area: ', sum(areas), 'median: ', numpy.median(areas))


				# fig = plt.figure(figsize = (8,4))	

				# ax = plt.subplot(121)
				# ax.hist(areas, normed=0, fill=False, ec='black', lw=3, hatch='/')
				# ax.set_title("Area")
				# ax.set_xlabel('Square Kilometers')
				# ax.set_ylabel('Count')

				# ax.axis('normal')

				# ax = plt.subplot(122)
				# ax.set_title("Population")
				# ax.hist(pops, normed=0, fill=False, ec='black', lw=3, hatch='x')
				# ax.set_xlabel('Population (Thousands)')
				# ax.set_ylabel('Count')

				# ax.axis('normal')

				#ax.violinplot ([areas, pops], showmeans=False, showmedians=True)
				#ax.set_xticklabels(['Area', 'Population'])
				
				# plt.tight_layout()
				
				
				# plt.savefig(outputfmt.format(statename, i, 'stats'))
				# plt.close(fig)


		# show loss distribution
		fig = plt.figure(figsize = (8,8))
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
			

			ax.set_title(statename)
			ax.set_xlabel('Number of basestations')
			ax.set_ylabel('Loss (dB)')
			ax.axis('tight')
			plt.savefig(outputfmt.format(statename, i, 'loss'))			
			plt.close(fig)
		else:
			print ("no loss data, not creating loss plot.")
			