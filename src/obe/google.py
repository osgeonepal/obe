import argparse
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
from urllib.parse import urljoin

import geopandas as gpd
import pandas as pd
import s2sphere
from shapely import wkt
from tqdm import tqdm

BUILDING_BASE_URL = "https://storage.googleapis.com/open-buildings-data/v3/polygons_s2_level_6_gzip_no_header/"


def get_s2_tiles(bounds):
    """Get S2 cell IDs that cover the given bounds.

    Args:
        bounds: tuple of (minx, miny, maxx, maxy) in WGS84
    Returns:
        list of S2 cell tokens at level 6
    """
    min_lat, min_lon = bounds[1], bounds[0]  # y, x
    max_lat, max_lon = bounds[3], bounds[2]  # y, x

    p1 = s2sphere.LatLng.from_degrees(min_lat, min_lon)  # SW point
    p2 = s2sphere.LatLng.from_degrees(max_lat, max_lon)  # NE point

    region_rect = s2sphere.LatLngRect.from_point_pair(p1, p2)

    coverer = s2sphere.RegionCoverer()
    coverer.min_level = 6
    coverer.max_level = 6
    coverer.max_cells = 1000000

    covering = coverer.get_covering(region_rect)

    return [cell.to_token() for cell in covering]


def download_tile_buildings(
    tile_id: str, region_geometry
) -> Optional[gpd.GeoDataFrame]:
    """Download buildings for a single S2 tile."""
    # try:
    tile_url = urljoin(BUILDING_BASE_URL, f"{tile_id}_buildings.csv.gz")
    df = pd.read_csv(tile_url, compression="gzip", header=None)

    if len(df) == 0:
        return None

    df.columns = [
        "latitude",
        "longitude",
        "area_in_meters",
        "confidence",
        "geometry_wkt",
        "full_plus_code",
    ]
    geometries = df["geometry_wkt"].apply(wkt.loads)

    gdf = gpd.GeoDataFrame(
        df.drop("geometry_wkt", axis=1), geometry=geometries, crs="EPSG:4326"
    )
    return gdf[gdf.geometry.within(region_geometry)]


def process_building_footprints(aoi_input):
    """Process building footprints with concurrent downloads."""
    if isinstance(aoi_input, str):
        aoi_gdf = gpd.read_file(aoi_input)
    elif isinstance(aoi_input, dict):
        aoi_gdf = gpd.GeoDataFrame.from_features(aoi_input["features"])
    else:
        raise ValueError(
            "aoi_input must be either a file path (str) or a GeoJSON dictionary"
        )

    all_buildings = []
    for aoi_row in aoi_gdf.itertuples():
        region_geometry = aoi_row.geometry
        bounds = region_geometry.bounds
        tile_ids = get_s2_tiles(bounds)

        print(f"Found {len(tile_ids)} S2 tiles covering the AOI")

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_tile = {
                executor.submit(
                    download_tile_buildings, tile_id, region_geometry
                ): tile_id
                for tile_id in tile_ids
            }

            for future in tqdm(
                as_completed(future_to_tile),
                total=len(tile_ids),
                desc="Downloading tiles",
            ):
                # try:
                gdf = future.result()
                if gdf is not None and not gdf.empty:
                    all_buildings.append(gdf)
            # except Exception as e:
            #     # raise e
            #     print(f"Error processing tile: {e}")

    if all_buildings:
        return pd.concat(all_buildings, ignore_index=True)
    else:
        return gpd.GeoDataFrame(
            columns=[
                "latitude",
                "longitude",
                "area_in_meters",
                "confidence",
                "geometry",
                "full_plus_code",
            ],
            crs="EPSG:4326",
        )


def main():
    parser = argparse.ArgumentParser(
        description="Process Google global building footprints within a given area of interest (AOI)."
    )
    parser.add_argument(
        "--input",
        help="Path to the input GeoJSON file containing the AOI",
        required=True,
    )
    parser.add_argument(
        "--output",
        help="Path to save the output file containing the building footprints",
    )
    parser.add_argument(
        "--format",
        help="Output format: geojson, geopackage, or shapefile",
        default="geojson",
        choices=["geojson", "geopackage", "shapefile"],
    )
    args = parser.parse_args()

    print("Starting the processing of building footprints...")
    result_gdf = process_building_footprints(args.input)
    print(f"Processed {len(result_gdf)} building footprints.")

    if not args.output:
        input_filename = os.path.splitext(os.path.basename(args.input))[0]
        args.output = f"{input_filename}_google_buildings.{args.format}"

    print(f"Saving results to {args.output}...")

    if args.format == "geojson":
        result_gdf.to_file(args.output, driver="GeoJSON")
    elif args.format == "geopackage":
        result_gdf.to_file(args.output, driver="GPKG")
    elif args.format == "shapefile":
        result_gdf.to_file(args.output, driver="ESRI Shapefile")

    print(f"Results successfully saved to {args.output}.")


if __name__ == "__main__":
    main()
