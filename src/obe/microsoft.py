import argparse
import os
import tempfile

import geopandas as gpd
import mercantile
import pandas as pd
from shapely import geometry
from tqdm import tqdm

DATASET_SOURCE_URL = (
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv"
)


def process_building_footprints(aoi_input, location):
    if isinstance(aoi_input, str):
        aoi_gdf = gpd.read_file(aoi_input)
    elif isinstance(aoi_input, dict):
        aoi_gdf = gpd.GeoDataFrame.from_features(aoi_input["features"])
    else:
        raise ValueError(
            "aoi_input must be either a file path (str) or a GeoJSON dictionary"
        )

    df = pd.read_csv(
        DATASET_SOURCE_URL,
        dtype=str,
    )
    if location not in df["Location"].unique():
        raise ValueError(
            f"Invalid location: {location}. Accepted values are: {df['Location'].unique()}"
        )

    combined_gdf = gpd.GeoDataFrame()
    idx = 0

    for aoi_row in aoi_gdf.itertuples():
        aoi_shape = aoi_row.geometry
        minx, miny, maxx, maxy = aoi_shape.bounds

        quad_keys = set()
        for tile in list(mercantile.tiles(minx, miny, maxx, maxy, zooms=9)):
            quad_keys.add(mercantile.quadkey(tile))
        quad_keys = list(quad_keys)
        print(f"The input area spans {len(quad_keys)} tiles: {quad_keys}")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_fns = []
            for quad_key in tqdm(quad_keys):
                rows = df[(df["QuadKey"] == quad_key) & (df["Location"] == location)]
                if rows.shape[0] == 1:
                    url = rows.iloc[0]["Url"]

                    df2 = pd.read_json(url, lines=True)
                    df2["geometry"] = df2["geometry"].apply(geometry.shape)

                    gdf = gpd.GeoDataFrame(df2, crs=4326)
                    fn = os.path.join(tmpdir, f"{quad_key}.geojson")
                    tmp_fns.append(fn)
                    if not os.path.exists(fn):
                        gdf.to_file(fn, driver="GeoJSON")
                elif rows.shape[0] > 1:
                    raise ValueError(f"Multiple rows found for QuadKey: {quad_key}")
                else:
                    raise ValueError(f"QuadKey not found in dataset: {quad_key}")

            for fn in tmp_fns:
                gdf = gpd.read_file(fn)
                gdf = gdf[gdf.geometry.within(aoi_shape)]
                gdf["id"] = range(idx, idx + len(gdf))
                idx += len(gdf)
                combined_gdf = pd.concat([combined_gdf, gdf], ignore_index=True)

    combined_gdf = combined_gdf.to_crs("EPSG:4326")

    return combined_gdf


def main():
    parser = argparse.ArgumentParser(
        description="Process microsoft global building footprints within a given area of interest (AOI)."
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
        "--location",
        help="Location to filter the dataset. Accepted values are from the dataset source.",
        required=True,
    )
    parser.add_argument(
        "--format",
        help="Output format: geojson, geopackage, or shapefile",
        default="geojson",
        choices=["geojson", "geopackage", "shapefile"],
    )
    args = parser.parse_args()

    result_gdf = process_building_footprints(args.input, args.location)
    print(f"Processed {len(result_gdf)} building footprints")

    if not args.output:
        input_filename = os.path.splitext(os.path.basename(args.input))[0]
        args.output = f"{input_filename}_microsoft_buildings.{args.format}"
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
