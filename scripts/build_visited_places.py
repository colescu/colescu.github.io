"""Build the static visited-place shapes from _data/visited_places.yml.

Requires: pip install -r scripts/map-requirements.txt
"""

import argparse
import json
import shutil
import tempfile
import unicodedata
import urllib.request
import urllib.parse
from pathlib import Path

import fiona
import requests
from fiona.transform import transform_geom
import yaml
from shapely.geometry import Point, mapping, shape
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_admin_1_states_provinces.zip"
ADMIN_NAMES = {"United States": "United States of America"}
REGION_ALIASES = {("Greece", "Central Macedonia"): "Kentriki Makedonia"}
US_STATE_FIPS = {"NY": "36", "NJ": "34"}
US_PLACE_URL = "https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_{state}_place_500k.zip"
AUSTRIA_MUNICIPALITY_URL = "https://gis.geosphere.at/maps/rest/services/grenzen/admin_grenzen_oesterreich/MapServer/2/query"
SLOVAKIA_MUNICIPALITY_URL = "https://opendata.skgeodesy.sk/static/ZBGIS/usj/ah_shp_0_sjtsk03.zip"
GREECE_MUNICIPAL_UNIT_URL = "https://sdigmap.tee.gov.gr/mapping/rest/services/UDM/UDM_SERVICE_ELSTAT/MapServer/5/query"
GREECE_REGIONAL_UNIT_URL = "https://geohub.necca.gov.gr/server/rest/services/ELBIOS-EXTERNAL_DATA/perifereiakes_enotites/MapServer/0/query"


def normalized(value):
    return "".join(
        character for character in unicodedata.normalize("NFKD", str(value).casefold())
        if not unicodedata.combining(character) and character.isalnum()
    )


def get_admin1(archive_path):
    return fiona.open("zip://" + archive_path.resolve().as_posix())


def region_names(feature, keys):
    properties = feature["properties"]
    return {normalized(properties[key]) for key in keys if properties.get(key)}


def country_geometry(feature):
    geometry = shape(feature["geometry"])
    if feature["properties"].get("name") == "China":
        # The border follows China's POV, but a visit to mainland China does
        # not color Taiwan or its nearby islands as visited.
        polygons = [
            polygon for polygon in geometry.geoms
            if not (118 < polygon.representative_point().x < 124
                    and 20 < polygon.representative_point().y < 27)
        ]
        geometry = type(geometry)(polygons)
    return geometry


def make_feature(name, geometry, kind, country=None):
    properties = {"name": name, "kind": kind}
    if country:
        properties["country"] = country
    return {"type": "Feature", "properties": properties, "geometry": mapping(geometry)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-regions", metavar="COUNTRY", help="show available region names")
    parser.add_argument("--source-zip", type=Path, help="use a previously downloaded Natural Earth archive")
    parser.add_argument("--us-places-dir", type=Path, help="use previously downloaded US place archives")
    parser.add_argument("--slovakia-source-zip", type=Path, help="use a previously downloaded Slovak municipality archive")
    args = parser.parse_args()

    config = yaml.safe_load((ROOT / "_data/visited_places.yml").read_text(encoding="utf-8"))
    whole_countries = config.get("countries") or []
    selected_regions = config.get("regions") or {}
    region_exclusions = config.get("region_exclusions") or {}
    selected_regional_units = config.get("regional_units") or {}
    selected_places = config.get("places") or {}
    overlap = ((set(whole_countries) & set(selected_regions))
               | (set(whole_countries) & set(selected_regional_units))
               | (set(whole_countries) & set(selected_places)))
    if overlap:
        parser.error(f"A whole country cannot also have regions or places: {sorted(overlap)}")

    world = json.loads((ROOT / "assets/data/world-china-view.geojson").read_text(encoding="utf-8"))
    by_name = {feature["properties"]["name"]: feature for feature in world["features"]}
    missing = (set(whole_countries) | set(selected_regions)
               | set(selected_regional_units) | set(selected_places)) - set(by_name)
    if missing:
        parser.error(f"Unknown countries in _data/visited_places.yml: {sorted(missing)}")

    features = [make_feature(name, country_geometry(by_name[name]), "country") for name in whole_countries]

    if selected_regions or args.list_regions:
        with tempfile.TemporaryDirectory() as temp_dir:
            if args.source_zip:
                archive = args.source_zip
            else:
                archive = Path(temp_dir) / "ne_admin1.zip"
                print("Downloading Natural Earth regional boundaries...")
                urllib.request.urlretrieve(SOURCE_URL, archive)

            with get_admin1(archive) as source:
                admin_features = [
                    feature for feature in source
                    if feature["properties"].get("admin") in {
                        ADMIN_NAMES.get(name, name) for name in selected_regions
                    } | ({ADMIN_NAMES.get(args.list_regions, args.list_regions)} if args.list_regions else set())
                ]

            if args.list_regions:
                country_admin = ADMIN_NAMES.get(args.list_regions, args.list_regions)
                names = sorted({
                    value for feature in admin_features
                    if feature["properties"].get("admin") == country_admin
                    for key in ("name_en", "name", "region", "geonunit")
                    if (value := feature["properties"].get(key))
                    and (key != "geonunit" or value != country_admin)
                })
                if not names:
                    parser.error(f"No regions found for {args.list_regions}")
                print("\n".join(names))
                return

            for country, names in selected_regions.items():
                relevant = [
                    feature for feature in admin_features
                    if feature["properties"].get("admin") == ADMIN_NAMES.get(country, country)
                ]
                for name in names:
                    query = normalized(REGION_ALIASES.get((country, name), name))
                    # Prefer the actual state/province name. A broader label
                    # such as France's region or UK's geonunit is only used
                    # when no first-order feature has that name.
                    matches = [
                        feature for feature in relevant
                        if query in region_names(feature, ("name", "name_en"))
                    ]
                    if not matches:
                        matches = [
                            feature for feature in relevant
                            if query in region_names(feature, ("region", "geonunit"))
                        ]
                    if not matches:
                        parser.error(f"No region '{name}' found in {country}. Run --list-regions '{country}' to see names.")
                    geometry = unary_union([shape(feature["geometry"]) for feature in matches])
                    for exclusion in region_exclusions.get(country, {}).get(name, []):
                        point = Point(*exclusion["point"])
                        polygons = list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else [geometry]
                        hits = [polygon for polygon in polygons if polygon.contains(point)]
                        if len(hits) != 1:
                            parser.error(f"Expected one island polygon for {exclusion['name']} in {country}/{name}; found {len(hits)}")
                        geometry = unary_union([polygon for polygon in polygons if not polygon.contains(point)])
                    features.append(make_feature(name, geometry, "region", country))

    for country, units in selected_regional_units.items():
        if country != "Greece":
            parser.error(f"Regional-unit boundaries are currently supported for Greece only: {country}")
        for unit in units:
            object_id = str(unit["object_id"])
            params = urllib.parse.urlencode({
                "where": f"OBJECTID={object_id}",
                "outFields": "OBJECTID,NAME_ENG",
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "geojson",
            })
            with urllib.request.urlopen(f"{GREECE_REGIONAL_UNIT_URL}?{params}") as response:
                data = json.load(response)
            matches = data.get("features", [])
            expected_name = f"Regional Unit of {unit['name']}"
            if (len(matches) != 1
                    or str(matches[0]["properties"].get("OBJECTID")) != object_id
                    or matches[0]["properties"].get("NAME_ENG") != expected_name):
                parser.error(f"Expected Greek regional unit {unit['name']} ({object_id}); found {len(matches)}")
            feature = make_feature(unit["name"], shape(matches[0]["geometry"]), "regional_unit", country)
            feature["properties"]["object_id"] = object_id
            features.append(feature)

    if selected_places:
        with tempfile.TemporaryDirectory() as temp_dir:
            for country, places in selected_places.items():
                if country == "Austria":
                    for place in places:
                        municipality_id = str(place["municipality_id"])
                        params = urllib.parse.urlencode({
                            "where": f"g_id='{municipality_id}'",
                            "outFields": "g_id,g_name",
                            "returnGeometry": "true",
                            "outSR": "4326",
                            "f": "geojson",
                        })
                        with urllib.request.urlopen(f"{AUSTRIA_MUNICIPALITY_URL}?{params}") as response:
                            data = json.load(response)
                        matches = data.get("features", [])
                        if len(matches) != 1 or matches[0]["properties"].get("g_name") != place["name"]:
                            parser.error(f"Expected Austrian municipality {place['name']} ({municipality_id}); found {len(matches)}")
                        feature = make_feature(place["name"], shape(matches[0]["geometry"]), "place", country)
                        feature["properties"]["municipality_id"] = municipality_id
                        features.append(feature)
                    continue
                if country == "Slovakia":
                    if args.slovakia_source_zip:
                        archive = args.slovakia_source_zip
                    else:
                        archive = Path(temp_dir) / "slovakia_admin.zip"
                        print("Downloading Slovak municipality boundaries...")
                        with requests.get(SLOVAKIA_MUNICIPALITY_URL, stream=True, timeout=120) as response:
                            response.raise_for_status()
                            with archive.open("wb") as target:
                                shutil.copyfileobj(response.raw, target)
                    with fiona.open("zip://" + archive.resolve().as_posix(), layer="obec_0") as source:
                        municipalities = list(source)
                        for place in places:
                            prefix = place["municipality_prefix"]
                            matches = [feature for feature in municipalities if feature["properties"].get("NM4", "").startswith(prefix)]
                            expected = int(place["expected_parts"])
                            if len(matches) != expected:
                                parser.error(f"Expected {expected} Slovak municipalities for {place['name']}; found {len(matches)}")
                            geometry = unary_union([
                                shape(transform_geom(source.crs, "EPSG:4326", feature["geometry"]))
                                for feature in matches
                            ])
                            features.append(make_feature(place["name"], geometry, "place", country))
                    continue
                if country == "Greece":
                    for place in places:
                        unit_id = str(place["municipal_unit_id"])
                        params = urllib.parse.urlencode({
                            "where": f"OBJECTID={unit_id}",
                            "outFields": "OBJECTID,NAME_GR",
                            "returnGeometry": "true",
                            "outSR": "4326",
                            "f": "geojson",
                        })
                        with urllib.request.urlopen(f"{GREECE_MUNICIPAL_UNIT_URL}?{params}") as response:
                            data = json.load(response)
                        matches = data.get("features", [])
                        if len(matches) != 1 or str(matches[0]["properties"].get("OBJECTID")) != unit_id:
                            parser.error(f"Expected one Greek municipal unit for {place['name']} ({unit_id}); found {len(matches)}")
                        feature = make_feature(place["name"], shape(matches[0]["geometry"]), "place", country)
                        feature["properties"]["municipal_unit_id"] = unit_id
                        features.append(feature)
                    continue
                if country != "United States":
                    parser.error(f"City boundaries are currently supported for Austria, Greece, Slovakia, and the United States only: {country}")
                for place in places:
                    state = place["state"]
                    geoid = str(place["geoid"])
                    if state not in US_STATE_FIPS:
                        parser.error(f"Unsupported US state for city boundaries: {state}")
                    code = US_STATE_FIPS[state]
                    if args.us_places_dir:
                        archive = args.us_places_dir / f"us_{code}_places.zip"
                    else:
                        archive = Path(temp_dir) / f"us_{code}_places.zip"
                        if not archive.exists():
                            print(f"Downloading Census place boundaries for {state}...")
                            urllib.request.urlretrieve(US_PLACE_URL.format(state=code), archive)
                    with get_admin1(archive) as source:
                        matches = [feature for feature in source if feature["properties"].get("GEOID") == geoid]
                    if len(matches) != 1:
                        parser.error(f"Expected one Census place with GEOID {geoid} in {state}; found {len(matches)}")
                    feature = make_feature(place["name"], shape(matches[0]["geometry"]), "place", country)
                    feature["properties"]["state"] = state
                    features.append(feature)

    target = ROOT / "assets/data/visited-places.geojson"
    target.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(features)} visited areas to {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
