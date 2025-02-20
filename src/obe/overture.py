import argparse
import os
import subprocess
import tempfile

import geopandas as gpd
import pandas as pd


def process_building_footprints(aoi_input):
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
        bbox = aoi_shape.bounds
        bbox_str = ",".join(map(str, bbox))
        print(f"Processing AOI with bounding box: {bbox_str}")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, f"output_buildings.geojson")
            cmd = [
                "overturemaps",
                "download",
                "-f",
                "geojson",
                "--bbox",
                bbox_str,
                "-o",
                output_file,
                "--type",
                "building",
                # "-cty",
                # "building",
            ]

            try:
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                while True:
                    output = process.stdout.readline()
                    if output == "" and process.poll() is not None:
                        break
                    if output:
                        print(output.strip())
                rc = process.poll()
                if rc != 0:
                    stderr = process.stderr.read()
                    raise RuntimeError(f"Error downloading data: {stderr}")

                gdf = gpd.read_file(output_file)
                gdf = gdf[gdf.geometry.within(aoi_shape)]
                gdf["id"] = range(idx, idx + len(gdf))
                idx += len(gdf)
                combined_gdf = pd.concat([combined_gdf, gdf], ignore_index=True)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Error downloading data: {e.stderr}")

    combined_gdf = combined_gdf.to_crs("EPSG:4326")

    return combined_gdf


def main():
    parser = argparse.ArgumentParser(
        description="Process Overture Maps building footprints within a given area of interest (AOI)."
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
        args.output = f"{input_filename}_overture_buildings.{args.format}"

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
