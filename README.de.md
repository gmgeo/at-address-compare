# Qualitätssicherung für österreichische Adressen

(also available in [English](https://github.com/gmgeo/at-address-compare/blob/master/README.md))

Dieses Python-Package (ataddrcompare) vergleicht österreichische Adressen
in OpenStreetMap mit den Adressdaten des Bundesamts für Eich- und
Vermessungswesen (BEV). Es arbeitet auf Gemeindeebene mit der
Gemeindekennzahl (GKZ) oder mit dem Gemeindenamen (der zur GKZ aufgelöst wird).

## Einsatzmöglichkeiten

* Darstellung der Adressabdeckung einer Gemeinde
* Darstellung der Adressabdeckung einzelner Straßen
* in OSM fehlende Hausnummern erkennen
* in OSM vorhandene, aber offiziell fehlende Hausnummern erkennen
* Schreibfehler in Straßennamen erkennen
* falsche Hausnummer-Straße-Zuordnungen erkennen

## Installation

Installation von Python 2 oder 3 mit Package Manager pip, dann

`pip install ataddrcompare`

## Einsatzbeispiel Villach (GKZ 20201)

* Konverter-Skript für BEV Adressdaten [holen](https://github.com/scubbx/convert-bev-address-data-python) - mittles "Clone or download" und
"Download ZIP"
* ZIP-Datei entpacken, in den Ordner wechseln und `python convert-addresses.py -gkz` ausführen, Skript sollte automatisch die Adressdaten herunterladen, das Python GDAL Modul (`python-gdal` oder `python3-gdal` auf Ubuntu) wird benötigt
* opt. Adressdatensatz vom BEV [selbst herunterladen](http://www.bev.gv.at/portal/page?_pageid=713,2601271&_dad=portal&_schema=PORTAL) und die ZIP-Datei in den Ordner vom Skript legen

Dann `ataddrcompare --html --timeout 60 bev_addresses.csv 20201 > villach.html`
ausführen. Das Programm holt sich nun die Adressdaten für die angegebene
Gemeinde aus OSM via Overpass API, vergleicht die Daten mit den angegebenen
offiziellen Daten und gibt das Ergebnis als HTML oder Text aus.

Die Parameter bedeuten folgendes:

* `--html` HTML Ausgabe, wenn weggelassen wird reiner Text ausgegeben
* `--timeout 60` Timeout der Overpass API Abfrage in Sekunden, sinnvoll bei großen Gemeinden
* `bev_addresses.csv` Angabe der CSV-Datei mit den offiziellen Adressdaten (kommt vom Konverter-Skript)
* `20201` GKZ von Villach (auch Angabe von `Villach` möglich)
* `> villach.html` Ausgabedatei, ansonsten erfolgt die Ausgabe auf die Konsole

## ähnliche Werkzeuge

[Hausnummernauswertung auf regio-osm.de](http://www.regio-osm.de/hausnummerauswertung/) - ähnliche
Darstellung und Inspiration für dieses Werkzeug. Dieses Skript soll als
Ergänzung zu diesem Angebot verstanden werden, da damit eigenständige und
häufige Auswertungen (ohne etwaige Wartezeit bzw. Serverlast für
regio-osm.de) möglich sind. Allerdings bietet das Skript keine zeitliche
Historie und regio-osm.de zeigt weitergehende Details an.

## Beitragen

Verbesserungen (Pull Requests) und Fehlermeldungen (Issues) sind willkommen.

## Lizenz

MIT License
