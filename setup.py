from setuptools import setup

setup(
  name = 'at-address-compare',
  packages = ['ataddrcompare'],
  version = '0.3.0',
  entry_points = {
    'console_scripts': ['ataddrcompare = ataddrcompare.ataddrcompare:main']
  },
  install_requires = ['overpass'],
  description = 'Address comparison of OSM data with official open data for Austria.',
  author = 'Michael Glanznig',
  url = 'https://github.com/gmgeo/at-address-compare',
  download_url = 'https://github.com/gmgeo/at-address-compare/tarball/0.3.0',
  keywords = ['Austria', 'OSM', 'OpenStreetMap', 'OpenData', 'addresses', 'address', 'compare'],
  license = 'MIT',
  classifiers = [],
  package_data =  {
    'ataddrcompare': ['template.txt', 'template.html']
  }
)
