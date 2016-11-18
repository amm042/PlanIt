"""
create network node locations based on population density.

"""

from Network import Node, Network

if __name__=="__main__":
	basestation = Node('Bucknell', 40.954910, -76.881304, 50)
	net = Network(basestation)



	import fiona

	fc = fiona.open('GENZ2010/gz_2010_42_140_00_500k.shp')
	print (fc.schema)



