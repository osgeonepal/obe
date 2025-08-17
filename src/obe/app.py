import argparse
import os

from .google import process_building_footprints as process_google
from .microsoft import process_building_footprints as process_microsoft
from .osm import process_osm_data
from .overture import process_building_footprints as process_overture


def get_output_extension(file_format):
    """Get the appropriate file extension for each file_format."""
    file_format_extensions = {
        "geojson": ".geojson",
        "geopackage": ".gpkg",
        "shapefile": ".shp",
        "geojsonseq": ".geojsonseq",
        "geoparquet": ".parquet",
    }
    return file_format_extensions[file_format]


def download_buildings(
    source,
    input_path,
    output_path,
    format=None,
    location=None,
):
    source = source.lower()
    file_format = format.lower() if format else None
    if source == "google":
        result_gdf = process_google(input_path)
    elif source == "microsoft":
        if not location:
            raise ValueError("Location is required for Microsoft data source.")
        result_gdf = process_microsoft(input_path, location)
    elif source == "osm":
        result_gdf = process_osm_data(input_path)
    elif source == "overture":
        result_gdf = process_overture(input_path)
    else:
        raise ValueError(f"Unknown source: {source}")

    print(f"Processed {len(result_gdf)} building footprints.")

    if file_format:
        if not output_path:
            input_filename = os.path.splitext(os.path.basename(input_path))[0]
            extension = get_output_extension(file_format)
            output_path = f"{input_filename}_{source}_buildings{extension}"
        print(f"Saving results to {output_path}...")
        if file_format == "geojson":
            result_gdf.to_file(output_path, driver="GeoJSON")
        elif file_format == "geopackage":
            result_gdf.to_file(output_path, driver="GPKG")
        elif file_format == "shapefile":
            result_gdf.to_file(output_path, driver="ESRI Shapefile")
        elif file_format == "geojsonseq":
            result_gdf.to_file(output_path, driver="GeoJSONSeq")
        elif file_format == "geoparquet":
            result_gdf.to_parquet(output_path)

    return result_gdf


def main():
    parser = argparse.ArgumentParser(
        description="Downloads open building footprints from various data sources within a given area of interest (AOI)."
    )
    parser.add_argument(
        "--source",
        help="Data source: google, microsoft, osm, overture",
        required=True,
        choices=["google", "microsoft", "osm", "overture"],
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
        help="Output file_format: geojson, geojsonseq, geoparquet, geopackage, or shapefile",
        choices=["geojson", "geojsonseq", "geoparquet", "geopackage", "shapefile"],
    )
    parser.add_argument(
        "--location",
        help="Location to filter the dataset (required for Microsoft data source)",
    )

    args = parser.parse_args()

    download_buildings(
        args.source,
        args.input,
        args.output,
        args.format,
        args.location,
    )


if __name__ == "__main__":
    main()
