# Updating visited places

Edit `_data/visited_places.yml`. Whole countries go under `countries`. To color only selected regions, remove that country from `countries` and list the regions under `regions`, as Spain does now. A country can have both `regions` and `places`, as Austria does: Vienna uses its state boundary, while Salzburg uses its municipality boundary. For Austria, add a `municipality_id` from the official municipality layer. For Greece, add a `municipal_unit_id` from the 2021 ELSTAT municipal unit layer; Corinth uses its municipal unit so both modern and Ancient Corinth are included without shading the whole Peloponnese. For Slovakia, add a `municipality_prefix` and `expected_parts` from the official municipality layer; Bratislava combines its 17 boroughs into one city outline. For the US, add a Census `geoid` and two-letter `state`.

Greek regional units smaller than a full administrative region go under `regional_units` with their name and the official boundary service's `OBJECTID`. Messinia covers Messini and Voidokilia Beach; Argolida covers Mycenae, Epidaurus, and Nafplion without shading the whole Peloponnese.

When a visited region contains an unvisited detached island, list it under `region_exclusions` with a point inside that island's polygon. Kythira and Antikythera are excluded from Attica this way.

To see the available region names, run:

```sh
python scripts/build_visited_places.py --list-regions Japan
```

Then rebuild the map data:

```sh
python -m pip install -r scripts/map-requirements.txt
python scripts/build_visited_places.py
```

The script writes `assets/data/visited-places.geojson`. Commit that file with the YAML change so the GitHub Pages site displays the update. The script downloads [Natural Earth's regional boundaries](https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-1-states-provinces/), [Greek regional-unit boundaries](https://geohub.necca.gov.gr/server/rest/services/ELBIOS-EXTERNAL_DATA/perifereiakes_enotites/MapServer/0), [US Census place boundaries](https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.2025.html), [Austria's municipality boundary](https://gis.geosphere.at/maps/rest/services/grenzen/admin_grenzen_oesterreich/MapServer/2), [Greece's 2021 municipal units](https://sdigmap.tee.gov.gr/mapping/rest/services/UDM/UDM_SERVICE_ELSTAT/MapServer/5), and [Slovakia's municipality boundaries](https://www.gku.sk/geoportal-en/zbgis/download/) when those places are configured. Visitors' browsers download only the resulting map data. Country outlines come from the existing China-view map data. The China country fill excludes Taiwan.
