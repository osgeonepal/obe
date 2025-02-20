import argparse
import io
import json
import os
import time
import zipfile

import geopandas as gpd
import pandas as pd
import requests

OSM_API_URL = "https://api-prod.raw-data.hotosm.org/v1"


def get_geometry(geometry):
    if isinstance(geometry, dict):
        return geometry
    elif hasattr(geometry, "__geo_interface__"):
        return geometry.__geo_interface__
    else:
        raise ValueError("Invalid geometry format")


def request_osm_data(geometry, feature_type="building"):
    payload = {
        "fileName": "obe",
        "geometry": geometry,
        "filters": {"tags": {"all_geometry": {"join_or": {feature_type: []}}}},
        "geometryType": ["polygon"],
    }

    response = requests.post(
        f"{OSM_API_URL}/snapshot/",
        json=payload,
        headers={
            "accept": "application/json",
            "Content-Type": "application/json",
            "Referer": "obe-python-lib",
        },
    )
    response.raise_for_status()
    return response.json()


def poll_task_status(task_link):
    while True:
        response = requests.get(f"{OSM_API_URL}{task_link}")
        response.raise_for_status()
        res = response.json()
        if res["status"] in ["SUCCESS", "FAILED"]:
            return res
        time.sleep(2)


def download_snapshot(download_url):
    response = requests.get(download_url)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content), "r") as zip_ref:
        with zip_ref.open("obe.geojson") as file:
            return json.load(file)


def process_osm_data(aoi_input):
    if isinstance(aoi_input, str):
        aoi_gdf = gpd.read_file(aoi_input)
    elif isinstance(aoi_input, dict):
        aoi_gdf = gpd.GeoDataFrame.from_features(aoi_input["features"])
    else:
        raise ValueError(
            "aoi_input must be either a file path (str) or a GeoJSON dictionary"
        )

    combined_gdf = gpd.GeoDataFrame()
    idx = 0

    for aoi_row in aoi_gdf.itertuples():
        aoi_shape = aoi_row.geometry
        geometry = get_geometry(aoi_shape)

        task_response = request_osm_data(geometry)
        task_link = task_response.get("track_link")

        if not task_link:
            raise RuntimeError("No task link found in API response")

        result = poll_task_status(task_link)

        if result["status"] == "SUCCESS" and result["result"].get("download_url"):
            download_url = result["result"]["download_url"]
            osm_data = download_snapshot(download_url)

            gdf = gpd.GeoDataFrame.from_features(osm_data["features"], crs=4326)
            gdf = gdf[gdf.geometry.within(aoi_shape)]
            gdf["id"] = range(idx, idx + len(gdf))
            idx += len(gdf)
            combined_gdf = pd.concat([combined_gdf, gdf], ignore_index=True)

    combined_gdf = combined_gdf.to_crs("EPSG:4326")

    return combined_gdf


def main():
    parser = argparse.ArgumentParser(
        description="Process OSM data within a given area of interest (AOI)."
    )
    parser.add_argument(
        "--input",
        help="Path to the input GeoJSON file containing the AOI",
        required=True,
    )
    parser.add_argument(
        "--output",
        help="Path to save the output file containing the OSM data",
    )
    parser.add_argument(
        "--feature-type",
        help="Type of feature to download from OSM",
        default="building",
    )
    parser.add_argument(
        "--format",
        help="Output format: geojson, geopackage, or shapefile",
        default="geojson",
        choices=["geojson", "geopackage", "shapefile"],
    )
    args = parser.parse_args()

    result_gdf = process_osm_data(args.input, args.feature_type)
    print(f"Processed {len(result_gdf)} OSM features")

    if not args.output:
        input_filename = os.path.splitext(os.path.basename(args.input))[0]
        args.output = f"{input_filename}_osm_data.{args.format}"
    print(f"Saving results to {args.output}")

    if args.format == "geojson":
        result_gdf.to_file(args.output, driver="GeoJSON")
    elif args.format == "geopackage":
        result_gdf.to_file(args.output, driver="GPKG")
    elif args.format == "shapefile":
        result_gdf.to_file(args.output, driver="ESRI Shapefile")

    print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
