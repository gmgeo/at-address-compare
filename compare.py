#! /usr/bin/python

from __future__ import print_function

import sys, csv, argparse, overpass, StringIO, collections, datetime

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

	total = 0
	total_missing = 0
	print('Sorting output...', file=sys.stderr)
	streets = collections.OrderedDict(sorted(streets.items()))

	if args.html == False:
		print('Adresses of GKZ ' + str(args.filter) + '. Processed at ' + datetime.datetime.now().strftime("%Y-%m-%d %H:%M") + '.')
		print()
	else:
		print('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/></head><body>')
		print('<table><thead><tr><th>Street</th><th>%</th><th>not in OSM</th><th>not in GOV</th></tr></thead><tbody>')

	for street, data in streets.iteritems():
		total += data['count']
		total_missing += len(data['notosm'])
		countStr = ''
		if data['count'] > 0:
			countStr = str(round(100 - (len(data['notosm']) / float(data['count'])) * 100, 2)) + '%'
		
		if args.html == True:
			print('<tr>')
			print('<td>' + street.encode('utf-8') + '</td><td>' + countStr + '</td><td>' + ', '.join(data['notosm']).encode('utf-8') + '</td><td>' + ', '.join(data['notgov']).encode('utf-8') + '</td>')
			print('</tr>')
		else:
			print(street.encode('utf-8') + ':')
			if data['count'] > 0:
				print(countStr)
			print('not in OSM: ' + ', '.join(data['notosm']).encode('utf-8'))
			print('not in GOV: ' + ', '.join(data['notgov']).encode('utf-8'))
			if data['abbrev'] == True:
				print('abbreviated in OSM')
			print('')

	if args.html == True:
		print('</tbody></table></body>')
	else:
		print('Total: ' + str(round(100 - (total_missing / float(total)) * 100, 2)) + '%')

	print('Done.', file=sys.stderr)
