from __future__ import print_function

import argparse
import csv
import collections
import datetime
import overpass
import pkg_resources
import re
import sys
from string import Template

name_replace = {}
name_replace['Doktor'] = 'Dr.'
name_replace['Professor'] = 'Prof.'
name_replace['Sankt'] = 'St.'

def canonicalName(name):
	for key, value in name_replace.iteritems():
		name = name.replace(key, value)
	return name

def checkAbbreviation(name):
	for key, value in name_replace.iteritems():
		if value in name:
			return True
	return False

def callOverpass(api, query):
	'''Runs 'query' against the Overpass API and returns the response. Exits
	   the program in case of an error.'''
	try:
		response = api.Get(query, responseformat='json')
	except Exception as e:
		msg = ('There was an error while querying Overpass API: {}. '
		       'Exiting.'.format(type(e).__name__))
		sys.exit(msg)

	return response

def processOverpassData(response):
	'''Processes the data returned by the Overpass API.

	Returns a set of (streetname, housenumber) tuples and a second set
	containing the abbreviated steet names'''

	def extract_street_housenumber(tags):
		'''Helper function to extract the street (or the place) tag and
		   the housenumber. Returns 'None' in case of an error.'''
		street = tags.get('addr:street')
		place  = tags.get('addr:place')
		number = tags.get('addr:housenumber')

		if (not (street or place)) or (not number):
			return None

		number = number.lower()

		if street:
			return (street, number)
		return (place, number)

	if not 'elements' in response:
		return (set(), set())

	# Sort out the items with an 'addr:interpolation' tag.
	interpolations = []
	others = []
	ids = {}
	for element in response['elements']:
		ids[element['id']] = element
		if 'addr:interpolation' in element['tags']:
			interpolations.append(element)
		else:
			others.append(element)

	# result set
	osm = set()

	#
	# Process address interpolations
	#

	for i in interpolations:
		if not i['type'] == 'way':
			continue

		print("Processing interpolation #{} ".format(i['id']), file=sys.stderr)

		if not 'nodes' in i or len(i['nodes']) != 2:
			print("doesn't have exactly two nodes", file=sys.stderr)
			continue

		id_node_from = i['nodes'][0]
		id_node_to   = i['nodes'][1]

		if not ((id_node_from in ids) and (id_node_to in ids)):
			print("node IDs not in data set", file=sys.stderr)
			continue

		node_from = ids[id_node_from]
		node_to   = ids[id_node_to]

		street_number_from = extract_street_housenumber(node_from['tags'])
		street_number_to   = extract_street_housenumber(node_to  ['tags'])

		if (not street_number_from) or (not street_number_to):
			print("from/to node doesn't contain a valid address", file=sys.stderr)
			continue

		(street, hn_from) = street_number_from
		(_     , hn_to  ) = street_number_to

		street = canonicalName(street)

		ipl_type = i['tags']['addr:interpolation']
		osm.update(interpolateAddresses(ipl_type, street, hn_from, hn_to))

	#
	# Process remaining addresses
	#

	abbrev = set()
	for element in others:
		item = element['tags']
		street_number = extract_street_housenumber(element['tags'])
		if not street_number:
			continue

		street, number = street_number
		osm.add((canonicalName(street), number))

		if checkAbbreviation(street):
			abbrev.add(street)

	return (osm, abbrev)

def interpolateAddresses(ipl_type, street, hn_from, hn_to):
	'''Returns a set of interpolated addresses from 'hn_from' to 'hn_to'
	   according to 'ipl_type'.'''
	if ipl_type == 'alphabetic':
		regex = '\s*(\d+)\s*([a-z])?\s*'
		match_from = re.match(regex, hn_from)
		if not match_from:
			print('unable to parse first housenumber', file=sys.stderr)
			return set()

		regex = '\s*(\d+)\s*([a-z])\s*'
		match_to = re.match(regex, hn_to)
		if not match_to:
			print('unable to parse second housenumber', file=sys.stderr)
			return set()

		if match_from.group(1) != match_to.group(1):
			print("housenumbers don't match", file=sys.stderr)
			return set()

		number = match_from.group(1)

		if match_from.group(2):
			start = match_from.group(2)
		else:
			start = 'a'

		end = match_to.group(2)

		result = set()
		for c in [chr(x) for x in range(ord(start), ord(end) + 1)]:
			result.add((street, number + c))

		return result
	else:
		print('interpolation type "{}" not implemented'.format(ipl), file=sys.stderr)
		return set()

def processGovData(filename, gkz):
	'''Processes the BEV data.

	Returns a set of (streetname, housenumber) tuples.'''

	with open(filename) as f:
		gov_input = list(csv.DictReader(f, delimiter=';'))

		gov = set()
		for item in gov_input:
			if int(item['gkz']) == gkz:
				street = unicode(item['strasse'], 'utf-8')
				number = unicode(item['nummer'].lower(), 'utf-8')

				gov.add((canonicalName(street), number))

	return gov

def main():
	parser = argparse.ArgumentParser(description='Compares BEV address catalogue data with OSM address data.')
	parser.add_argument('gov',
	                    help='BEV address catalogue')
	parser.add_argument('filter',
	                    help='specify name or GKZ of municipality to filter for')
	parser.add_argument('--timeout',
	                    dest='timeout',
	                    type=int,
	                    default=25,
	                    help='specify Overpass API timeout value')
	parser.add_argument('--html',
	                    dest='html',
	                    action='store_true')
	args = parser.parse_args()

	api = overpass.API(timeout=args.timeout)

	try:
		gkz = int(args.filter)
	except ValueError:
		print('Trying to get GKZ for name from Overpass API...', file=sys.stderr)
		query = '''
		    relation["type"="boundary"]
		            ["admin_level"="8"]
		            ["name"="{}"]'''.format(args.filter)
		response = callOverpass(api, query)

		try:
			gkz = int(response['elements'][0]['tags']['ref:at:gkz'])
			print('GKZ = {}'.format(gkz), file=sys.stderr)
		except (KeyError, IndexError, ValueError):
			sys.exit('Could not match name to GKZ. Exiting.')

	print('Fetching data from Overpass API...', file=sys.stderr)

	query = '''
	    area["type"="boundary"]
	        ["admin_level"="8"]
	        ["ref:at:gkz"="{}"]->.searchArea;

	    (
	        node["addr:housenumber"](area.searchArea);
	         way["addr:housenumber"](area.searchArea);

	        way["addr:interpolation"](area.searchArea);
	    );'''.format(gkz)
	response = callOverpass(api, query)

	print('Processing data...', file=sys.stderr)

	(osm, osmabbrev) = processOverpassData(response)
	gov = processGovData(args.gov, gkz)

	streets = {}

	#
	# Add one item to 'streets' for every street that occurs in an address in
	# the data. For items that appear in the OSM data, abbreviated street names
	# are marked as such.
	#

	osm_streetnames = set([s for (s, n) in osm])
	gov_streetnames = set([s for (s, n) in gov])
	all_streetnames = osm_streetnames | gov_streetnames

	for streetname in all_streetnames:
		streets[streetname] = {'notosm': [], 'notgov': [], 'abbrev': False}
	for streetname in osmabbrev:
		streets[streetname]['abbrev'] = True

	#
	# For each address, check if it only appears in one of the data sets.
	#

	osm_only = osm - gov
	gov_only = gov - osm

	for s, n in osm_only:
		streets[s]['notgov'].append(n)
	for s, n in gov_only:
		streets[s]['notosm'].append(n)

	#
	# Calculate the total number of addresses in each street.
	#

	cnt_streetnames = collections.Counter([s for (s, n) in (osm | gov)])
	for (streetname, count) in cnt_streetnames.iteritems():
		streets[streetname]['count'] = count

	#
	# Generate output.
	#

	print('Sorting output...', file=sys.stderr)
	for street in streets:
		streets[street]['notosm'] = sorted(streets[street]['notosm'])
		streets[street]['notgov'] = sorted(streets[street]['notgov'])
	streets = collections.OrderedDict(sorted(streets.items()))
	writeOutput(streets, gkz, args.html)
	print('Done.', file=sys.stderr)

def writeOutput(streets, gkz, html):
	if html == False:
		templateFile = pkg_resources.resource_string(__name__, 'template.txt')
	else:
		templateFile = pkg_resources.resource_string(__name__, 'template.html')

	templateStr = Template(templateFile)

	detail = ''
	total = 0
	total_missing = 0
	for street, data in streets.iteritems():
		total += data['count']
		total_missing += len(data['notosm'])
		countStr = ''
		countPercent = 0
		if data['count'] > 0:
			countPercent = round(100 - (len(data['notosm']) / float(data['count'])) * 100, 2)
			countStr = str(countPercent) + '%'

		if html == True:
			detail += '<tr>'
			detail += '<td>' + street.encode('utf-8')
			if data['abbrev'] == True:
				detail += ' <a href="#abbrev"><sup>*</sup></a>'
			detail += '</td><td class="'
			if countPercent <= 20:
				detail += 'c20'
			if countPercent > 20 and countPercent <= 40:
				detail += 'c40'
			if countPercent > 40 and countPercent <= 60:
				detail += 'c60'
			if countPercent > 60 and countPercent <= 80:
				detail += 'c80'
			if countPercent > 80:
				detail += 'c100'
			detail += '">' + countStr + '</td><td>' + ', '.join(data['notosm']).encode('utf-8') + '</td><td>' + ', '.join(data['notgov']).encode('utf-8') + '&nbsp;</td>'
			detail += '</tr>' + '\n'
		else:
			detail += street.encode('utf-8') + ': '
			if data['count'] > 0:
				detail += countStr + ' \n'
			detail += 'not in OSM: ' + ', '.join(data['notosm']).encode('utf-8') + '\n'
			detail += 'not in GOV: ' + ', '.join(data['notgov']).encode('utf-8') + '\n'
			if data['abbrev'] == True:
				detail += 'abbreviated in OSM' + '\n'
			detail += '\n'

	substVars = {
		'gkz':gkz,
		'time':datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
		'total':round(100 - (total_missing / float(total)) * 100, 2),
		'detail':detail
	}

	print(templateStr.substitute(substVars))
