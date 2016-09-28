
import matplotlib.pyplot as plt
from descartes import PolygonPatch
from processSamplePoints import make_patch, plot_shapes
from pointSampler import PopulationBasedPointSampler
import pymongo
from pprint import pprint
from elevation import Elevation
import numpy

if __name__=="__main__":

	connection = pymongo.MongoClient('mongodb://owner:fei6huM4@eg-mongodb.bucknell.edu/ym015')
	db = connection.get_default_database()	

	#placename = "DuBois"
	placename = "Philadelphia"
	#placename = "Harrisburg"
	#placename = "St. Marys"
	#placename = "Parker"
	for placename in db['POINTRESULTS'].distinct('name'):


		outputfmt = "figures/places/{}_{}_{}.pdf"

		ps = PopulationBasedPointSampler()

		query = {'properties.LSAD': 'city', 'properties.STATE': '42', 'properties.NAME': placename}
		
		city_shp = list( db['GENZ2010_160'].find(query) )

		query = {'state': '42', 'name':placename}
		
		e = Elevation() # to look up point elevations.

		lossbynumbase = {}		
		loss_threshold= {}	
		for i, pointdoc in enumerate(db['POINTS'].find(query)):

			lqry = {'point_docid': pointdoc['_id']}

			if i == 0:
				for rsltdoc in db['POINTRESULTS'].find(lqry):
					lossbynumbase[rsltdoc['num_basestations']] = [x['min_loss'] for x in rsltdoc['nodes']]	
					loss_threshold[rsltdoc['num_basestations']] = [rsltdoc['loss_threshold']]
			else:
				for rsltdoc in db['POINTRESULTS'].find(lqry):
					lossbynumbase[rsltdoc['num_basestations']] += [x['min_loss'] for x in rsltdoc['nodes']]
					loss_threshold[rsltdoc['num_basestations']].append(rsltdoc['loss_threshold'])

			# stats are the same, so only do it once.
			if i == 0:

				fig = plt.figure(figsize = (8,8))
				ax = plt.subplot(111)

				#plot_shapes(ax, city_shp, filled= True, show_states = True, fc=lambda x:'red', alpha=0.99)
				plot_shapes(ax, city_shp, filled= False, show_states = True)

				plot_shapes(ax, pointdoc['shapes'], filled=True, show_states=True)

				# this is one way to do it
				# tract_shp = list(ps.get_tract_shapes_in_area(city_shp[0]))
				# plot_shapes(ax, tract_shp, filled= True, show_states = True)		

				
				elev_data = []
				for pt in pointdoc['points']:
					ax.plot(pt['coordinates'][0],pt['coordinates'][1], '.', color='black', ms=4, lw=2, alpha=0.75)
					elev_data.append(e.lookup(pt['coordinates']))

				ax.ticklabel_format(useOffset=False, style="plain")
				ax.set_title(placename)
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

				print("{} has {} tracts.".format(placename, len(pointdoc['shapes'])))
				areas = [sh['properties']['area']['effective'] / (1000.0**2) for sh in pointdoc['shapes']] # convert meters to KM
				pops = [sh['properties']['population']['effective']/1000.0 for sh in pointdoc['shapes']]

				#print (areas)
				#print (pops)
				print ('total pop: ', sum(pops), 'median: ', numpy.median(pops))
				print ('total area: ', sum(areas), 'median: ', numpy.median(areas))


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


		# show loss distribution
		fig = plt.figure(figsize = (8,8))
		ax = plt.subplot(111)

		bases = sorted(lossbynumbase.keys())

		if len(bases) > 0:
			ax.violinplot(
				[lossbynumbase[bs] for bs in bases],
				bases,
				showmeans=False, showmedians=True)
			ax.plot(bases, [numpy.median(loss_threshold[i]) for i in bases], '--', alpha=0.5, color='green', lw=2)
			ax.set_title(placename)
			ax.set_xlabel('Number of basestations')
			ax.set_ylabel('Loss (dB)')
			ax.axis('tight')
			plt.savefig(outputfmt.format(placename, i, 'loss'))			
			plt.close(fig)