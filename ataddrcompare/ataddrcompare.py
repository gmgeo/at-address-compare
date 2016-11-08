from __future__ import print_function

import argparse
import csv
import collections
import datetime
import overpass
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

	streets = {}
	api = overpass.API(timeout=args.timeout)

	try:
		args.filter = int(args.filter)
	except ValueError:
		print('Trying to get GKZ for name from Overpass API...', file=sys.stderr)
		try:
			response = api.Get('relation["type"="boundary"]["admin_level"="8"]["name"="' + args.filter + '"]', responseformat='json')
			try:
				args.filter = response['elements'][0]['tags']['ref:at:gkz']
				print('GKZ = ' + args.filter, file=sys.stderr)
			except (KeyError, IndexError):
				print('Could not match name to GKZ. Exiting.', file=sys.stderr)
				sys.exit()
		except Exception,e:
			print('There was an error while querying Overpass API: ' + type(e).__name__ + '. Exiting.', file=sys.stderr)
			sys.exit()

	print('Fetching data from Overpass API...', file=sys.stderr)

	query = 'area["type"="boundary"]["admin_level"="8"]["ref:at:gkz"="' + str(args.filter) + '"]->.searchArea;(node["addr:housenumber"](area.searchArea);way["addr:housenumber"](area.searchArea););'
	try:
		response = api.Get(query, responseformat="json")
	except Exception,e:
		print('There was an error while querying Overpass API: ' + type(e).__name__ + '. Exiting.', file=sys.stderr)
		sys.exit()

	print('Processing data...', file=sys.stderr)

	with open(args.gov) as f1:
		gov_input = list(csv.DictReader(f1, delimiter=';'))

		osm = {}
		if 'elements' in response and len(response['elements']) > 0:
			for element in response['elements']:
				item = element['tags']
				if ('addr:place' in item or 'addr:street' in item) and 'addr:housenumber' in item:
					item['number'] = item['addr:housenumber'].lower()
					if 'addr:street' in item:
						item['street'] = item['addr:street']
					else:
						item['street'] = item['addr:place']

					street = canonicalName(item['street'])
					if street not in streets:
						streets[street] = {}
						streets[street]['count'] = 0
						streets[street]['notosm'] = []
						streets[street]['notgov'] = []
						streets[street]['abbrev'] = checkAbbreviation(item['street'])

					try:
						del item['addr:street']
						del item['addr:place']
						del item['addr:housenumber']
					except KeyError:
						pass
					osm[street + ' ' + item['number']] = item

		gov = {}
		for item in gov_input:
			if int(item['gkz']) == args.filter:
				item['number'] = unicode(item['nummer'].lower(), 'utf-8')
				item['street'] = unicode(item['strasse'], 'utf-8')
				street = canonicalName(item['street'])

				if street not in streets:
					streets[street] = {}
					streets[street]['count'] = 0
					streets[street]['notosm'] = []
					streets[street]['notgov'] = []
					streets[street]['abbrev'] = False

				try:
					del item['nummer']
					del item['strasse']
					del item['Gemeinde']
					del item['plz']
					del item['gkz']
					del item['hausname']
					del item['x']
					del item['y']
				except KeyError:
					pass
				gov[street + ' ' + item['number']] = item

				streets[street]['count'] += 1
				if street + ' ' + item['number'] not in osm:
					streets[street]['notosm'].append(item['number'])

		for key, value in osm.iteritems():
			street = canonicalName(value['street'])
			if key not in gov:
				streets[street]['notgov'].append(value['number'])

		print('Sorting output...', file=sys.stderr)
		streets = collections.OrderedDict(sorted(streets.items()))
		writeOutput(streets, args.filter, args.html)
		print('Done.', file=sys.stderr)

def writeOutput(streets, gkz, html):
	if html == False:
		templateFile = open('template.txt')
	else:
		templateFile = open('template.html')

	templateStr = Template(templateFile.read())

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
