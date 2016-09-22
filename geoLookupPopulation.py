from census import Census
import requests
import pprint

class GeoPop():
	def __init__(self, api_key):
		self.census = Census(api_key)

	def get_location_codes(self, latitude, longitude, censusYear=None, 
			format='json', showall=False, 
			url='http://data.fcc.gov/api/block/find'):
		"""
		lookup using https://www.fcc.gov/general/census-block-conversions-api
		you will get a tuple of FIPS codes from most specific to least: 
			 Census Tract, County, State 
		"""

		q = {'latitude': latitude,
		 	 'longitude': longitude,
		 	 'format': format,
		 	 'showall': showall}
		if censusYear != None:
			q['censusYear'] = censusYear
								  
		r = requests.get(url, params=q).json()

		# reduce the data a bit to only FIPS codes
		# but the source has some other useful info
		#                    123456789012345  # 15 digit block
		#{'Block': {'FIPS': '421199808001002'},
		#    state  [2]      --
		#    county [3]        --- 
		#    tract  [6]           ------
		#    block  [4]                 ----
	 	# 'County': {'FIPS': '42119', 'name': 'Union'},
	 	# 'State': {'FIPS': '42', 'code': 'PA', 'name': 'Pennsylvania'},
		# 'executionTime': '145',
	 	# 'status': 'OK'}
	 	# The FIPS code will be None if the location is invalid.

		#pprint.pprint(r)

		if r['Block']['FIPS'] == None or r['County']['FIPS'] == None or r['State']['FIPS'] == None:
			return None, None, None

		# convert block number code to census tract code
		# county has to strip of the two digit state code
		return r['Block']['FIPS'][5:11], r['County']['FIPS'][2:], r['State']['FIPS']

	def get_population_acs5(self, state, county=None, tract=None, fields=["B01003_001E"], **kwargs):
		# state, county, and tract params are specified with FIPS codes.
		# override the default field if you want a different statistic
						
		if county != None and tract != None:
			ret = self.census.acs5.state_county_tract(fields, state, county, tract, **kwargs)
		elif county != None:
			ret = self.census.acs5.state_county(fields, state, county, **kwargs)
		else:
			ret = self.census.acs5.state(fields, state, **kwargs)

		#pprint.pprint(fields)
		#pprint.pprint(ret)
		if ret == []:
			return ret
		else:
			return [ret[0][k] for k in fields]

	def get_population_sf1(self, state, county=None, tract=None, fields=["P0010001"], **kwargs):
		# sf1 is more complete than acs5. but acs5 has more fields.
		# state, county, and tract params are specified with FIPS codes.
		# override the default field if you want a different statistic
		# fields from http://api.census.gov/data/2010/sf1/variables.json
		
		if county != None and tract != None:
			ret = self.census.sf1.state_county_tract(fields, state, county, tract, **kwargs)
		elif county != None:
			ret = self.census.sf1.state_county(fields, state, county, **kwargs)
		else:
			ret = self.census.sf1.state(fields, state, **kwargs)

		#pprint.pprint(fields)
		#pprint.pprint(ret)
		if ret == []:
			return ret
		else:
			return [ret[0][k] for k in fields]

	# helper functions below
	def get_population_state(lat, lon):
		b,c,s = self.get_location_codes(lat, lon)
		return self.get_population(s)
	def get_population_county(lat, lon):
		b,c,s = self.get_location_codes(lat, lon)
		return self.get_population(s, c)


if __name__=="__main__":
	"""
	do a sample lookup on breakiron Breakiron Engineering
	Lewisburg, PA 17837
	40.954910, -76.881304
	"""

	#import logging
	#logging.basicConfig(level=logging.DEBUG)

	# this is my api key do not distribute
	g = GeoPop("ca22eb30af97c6b471419d7fe22b9ce9a5d1fe8d")

	# different codes can be found here: http://api.census.gov/data/2014/acs5/variables.json
	# B01003_001E == total population
	

	# bucknell is tract 9808 --> returns 980800
	t,c,s = g.get_location_codes(40.954910, -76.881304)

	assert(s == '42')
	assert(c == '119')
	assert(t == '980800')

	# there is also a decimal tract, let's see what happens... tract 905.02
	# this works, it returns tract 090502 --> perfect	
	t,c,s = g.get_location_codes(40.97753560, -76.97112120)	
	assert(s == '42')
	assert(c == '119')
	assert(t == '090502')

	for locs in [(40.954910, -76.881304),		# breakiron
				 (40.97753560, -76.97112120), 	# some other tract in union county
				 (39.473471, -106.013966), 		# colorado location
				 (51.556346, -39.458618), 		# north atlantic ocean (should be zero/na!)
				 ]:

		t,c,s = g.get_location_codes(locs[0], locs[1])	

		print("Location {},{} == {} {} {}".format(locs[0], locs[1], s, c, t))

		test_sums = True
		print_pop = True

		if test_sums:

			#pprint.pprint((t,c,s))

			state = g.census.sf1.state(['P0010001'], s)

			if state == []:
				break

			#pprint.pprint(state)
			print("total state pop: {}".format(state[0]['P0010001']))

			all_counties = g.census.sf1.state_county(['P0010001'], s, '*')
				# each county has a dict like:
				#[
				#  {'P0010001': '44947', 'P0030001': '44947', 'county': '119', 'state': '42'},
				# ... more counties
				#]
			print("total pop in all counties: {}".format(sum([int(x['P0010001']) for x in all_counties])))

			assert (int(state[0]['P0010001']) == sum([int(x['P0010001']) for x in all_counties]))

			all_tracts = g.census.sf1.state_county_tract(['P0010001'], s, c, '*')

			#pprint.pprint(all_tracts)

			county = g.census.sf1.state_county(['P0010001'], s, c)
			# these two should match
			print("census pop in county: {}".format(county[0]['P0010001']))
			print("total pop in county: {}".format(sum([int(x['P0010001']) for x in all_tracts])))
			assert (int(county[0]['P0010001'])) == sum([int(x['P0010001']) for x in all_tracts])

			tract = g.census.sf1.state_county_tract(['P0010001'], s, c, t)
			print("pop in tract: {}".format(tract[0]))

		if print_pop:
			print("in the state [{}]:  {}".format(s, g.get_population_sf1(s)))
			print("in the county [{} {}]: {}".format(s,c , g.get_population_sf1(s,c)))
			print("in the tract [{} {} {}]:  {}".format(s,c,t, g.get_population_sf1(s, c, t)))

