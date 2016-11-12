# Quality Assurance for Austrian Addresses

(auch verfügbar in [Deutsch](https://github.com/gmgeo/at-address-compare/blob/masterREADME.de.md))

The python package ataddrcompare compares Austrian address data
in OpenStreetMap with address data of the Bundesamt für Eich- und
Vermessungswesen (BEV, Austrian land surveying agency). It operates on
municipality level and needs the Gemeindekennzahl (GKZ, Austrian municipality
 identifier) or the name of the municipality (will be transformed into the GKZ).

## Usage Possibilities

* Displaying address coverage of a municipality
* Displaying address coverage of streets
* detect missing house numbers in OSM
* detect officially missing house numbers that are present in OSM
* detect typos in street names
* detect house numbers that are associated to the wrong street name

## Installation

Install Python 2 or 3 with package manager pip, then run

`pip install ataddrcompare`

## Usage Example Villach (GKZ 20201)

* [Get](https://github.com/scubbx/convert-bev-address-data-python) the converter script for BEV address data - select "Clone or download" and
"Download ZIP"
* Extract the ZIP file, change into the directory of the script and run `python convert-addresses.py -gkz`, the script should automatically fetch address data, the Python GDAL module (`python-gdal` or `python3-gdal` on Ubuntu) is needed
* opt. [download](http://www.bev.gv.at/portal/page?_pageid=713,2601271&_dad=portal&_schema=PORTAL) BEV address data yourself and place the ZIP file in the script directory

Run `ataddrcompare --html --timeout 60 bev_addresses.csv 20201 > villach.html`.
The script now fetches address data of the municipality from OSM via Overpass
API, compares the data with the official data and outputs the result either as
HTML or plain text.

Meaning of parameters:

* `--html` HTML output, if left out plain text is emitted
* `--timeout 60` Timeout of the Overpass API query in seconds, useful for larger municipalities
* `bev_addresses.csv` CSV file of official BEV address data (emitted by converter script)
* `20201` GKZ of Villach (it is also possible to specify `Villach`)
* `> villach.html` output file, otherwise output is written to the console

## Related Tools

[Hausnummernauswertung on regio-osm.de](http://www.regio-osm.de/hausnummerauswertung/) - has similar
visualisation and inspired this tool. The script should be seen as additional
offer because it enables autonomous and repeated processing (without waiting
period or additional server load for regio-osm.de). On the other hand, the
script does not offer a history and regio-osm.de displays more detail.

## Contributing

Improvements (pull requests) and bug reports (issues) are welcome.

## License

MIT License
