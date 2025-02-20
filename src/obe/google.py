import argparse
import os
from typing import Optional

import geopandas as gpd
import pandas as pd
import shapely
from tqdm import tqdm

BUILDING_DOWNLOAD_PATH = "https://storage.googleapis.com/open-buildings-data/v3/polygons_s2_level_6_gzip_no_header"
TILES_URL = "https://researchsites.withgoogle.com/tiles.geojson"


def get_intersecting_tiles(
    region_geometry: shapely.geometry.base.BaseGeometry,
) -> gpd.GeoDataFrame:
    tiles_gdf = gpd.read_file(TILES_URL)
    return tiles_gdf[tiles_gdf.intersects(region_geometry)]


def download_tile_buildings(
    tile_url: str, region_geometry: shapely.geometry.base.BaseGeometry
) -> Optional[gpd.GeoDataFrame]:
    try:
        df = pd.read_csv(tile_url, compression="gzip")
        print(df.head(5))
        gdf = gpd.GeoDataFrame(
            df, geometry=gpd.points_from_xy(df[1], df[0]), crs="EPSG:4326"
        )
        gdf.columns = [
            "latitude",
            "longitude",
            "area_in_meters",
            "confidence",
            "geometry",
            "full_plus_code",
        ]
        return gdf[gdf.within(region_geometry)]
    except Exception as e:
        print(f"Error downloading tile from {tile_url}: {e}")
        raise e
        return None


def process_region(region_df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    all_buildings = []
    for aoi_row in region_df.itertuples():
        region_geometry = aoi_row.geometry
        intersecting_tiles = get_intersecting_tiles(region_geometry)
        print(f"Found {len(intersecting_tiles)} intersecting tiles for the region.")

        for _, tile in tqdm(
            intersecting_tiles.iterrows(),
            desc="Processing tiles",
            total=len(intersecting_tiles),
        ):
            gdf = download_tile_buildings(tile["tile_url"], region_geometry)
            if gdf is not None:
                all_buildings.append(gdf)

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


def process_building_footprints(aoi_input):
    if isinstance(aoi_input, str):
        aoi_gdf = gpd.read_file(aoi_input)
    elif isinstance(aoi_input, dict):
        aoi_gdf = gpd.GeoDataFrame.from_features(aoi_input["features"])
    else:
        raise ValueError(
            "aoi_input must be either a file path (str) or a GeoJSON dictionary"
        )

    return process_region(aoi_gdf)


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
