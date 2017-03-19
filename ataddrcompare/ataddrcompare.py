# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import csv
import collections
import datetime
import overpass
import pkg_resources
import sys
from string import Template

name_replace = {}
name_replace[u'Doktor'] = u'Dr.'
name_replace[u'Professor'] = u'Prof.'
name_replace[u'Sankt'] = u'St.'
name_replace[u'Straße'] = u'Str.'
name_replace[u'-von-'] = u'-v.-'
name_replace[u' von '] = u' v. '

def canonicalName(name):
	for key, value in name_replace.iteritems():
		name = name.replace(value, key)
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

	if not 'elements' in response:
		return (set(), set())

	osm = set()
	abbrev = set()
	for element in response['elements']:
		item = element['tags']
		if ('addr:place' in item or 'addr:street' in item) and \
		    'addr:housenumber' in item:
			if 'addr:street' in item:
				street = item['addr:street'].strip()
			else:
				street = item['addr:place']
			number = item['addr:housenumber'].lower().strip()

			# avoid adding empty streets and/or empty numbers
			if len(street) > 0 and len(number) > 0:
				osm.add((canonicalName(street), number))

			if checkAbbreviation(street):
				abbrev.add(canonicalName(street))

	return (osm, abbrev)

def processGovData(filename, gkz):
	'''Processes the BEV data.

	Returns a set of (streetname, housenumber) tuples.'''

	with open(filename) as f:
		gov_input = list(csv.DictReader(f, delimiter=';'))

		gov = set()
		for item in gov_input:
			if int(item['gkz']) == gkz:
				street = unicode(item['strasse'].strip(), 'utf-8')
				number = unicode(item['nummer'].lower().strip(), 'utf-8')

				# avoid adding empty streets and/or empty numbers
				if len(street) > 0 and len(number) > 0:
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
		streets[streetname] = {'notosm': [], 'notgov': [], 'abbrev': False, 'count': 0}
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

	cnt_streetnames = collections.Counter([s for (s, n) in (gov)])
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
		else:
			countStr = '?'

		if html == True:
			detail += '<tr>'
			detail += '<td>' + street.encode('utf-8')
			if data['abbrev'] == True:
				detail += ' <a href="#abbrev"><sup>*</sup></a>'
			detail += '</td><td class="'
			if data['count'] == 0:
				detail += 'c0'
			if data['count'] > 0 and countPercent <= 20:
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
