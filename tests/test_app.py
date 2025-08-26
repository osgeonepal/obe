import json
import os

import geopandas as gpd
import pytest

from obe.app import download_buildings

# Test data - Pokhara, Nepal area
TEST_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "coordinates": [
                    [
                        [83.96184435207743, 28.212767538129086],
                        [83.96184435207743, 28.20236573207498],
                        [83.97605449676462, 28.20236573207498],
                        [83.97605449676462, 28.212767538129086],
                        [83.96184435207743, 28.212767538129086],
                    ]
                ],
                "type": "Polygon",
            },
        }
    ],
}

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(TEST_DIR, "data")
OUTPUT_DIR = os.path.join(TEST_DIR, "outputs")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


@pytest.fixture
def test_geojson_path():
    """Create a GeoJSON file for testing."""
    geojson_path = os.path.join(DATA_DIR, "test_aoi.geojson")
    with open(geojson_path, "w") as f:
        json.dump(TEST_GEOJSON, f)
    return geojson_path


def test_google_buildings(test_geojson_path):
    """Test Google building footprint extraction."""
    result_file = os.path.join(OUTPUT_DIR, "google_buildings.geojson")

    download_buildings(
        source="google",
        input_path=test_geojson_path,
        output_path=result_file,
        format="geojson",
    )

    assert os.path.exists(result_file)
    gdf = gpd.read_file(result_file)
    assert len(gdf) > 0
    assert "area_in_meters" in gdf.columns
    assert "confidence" in gdf.columns


def test_microsoft_buildings(test_geojson_path):
    """Test Microsoft building footprint extraction."""
    result_file = os.path.join(OUTPUT_DIR, "microsoft_buildings.geojson")

    download_buildings(
        source="microsoft",
        input_path=test_geojson_path,
        output_path=result_file,
        format="geojson",
        location="Nepal",
    )

    assert os.path.exists(result_file)
    gdf = gpd.read_file(result_file)
    assert len(gdf) > 0

    assert "height" in gdf.columns, "Microsoft buildings should have 'height' attribute"
    assert "confidence" in gdf.columns, (
        "Microsoft buildings should have 'confidence' attribute"
    )
    assert "id" in gdf.columns, "Microsoft buildings should have 'id' attribute"


def test_osm_buildings(test_geojson_path):
    """Test OSM building footprint extraction."""
    result_file = os.path.join(OUTPUT_DIR, "osm_buildings.geojson")

    download_buildings(
        source="osm",
        input_path=test_geojson_path,
        output_path=result_file,
        format="geojson",
    )

    assert os.path.exists(result_file)
    gdf = gpd.read_file(result_file)
    assert len(gdf) > 0


def test_overture_buildings(test_geojson_path):
    """Test Overture building footprint extraction."""
    result_file = os.path.join(OUTPUT_DIR, "overture_buildings.geojson")

    download_buildings(
        source="overture",
        input_path=test_geojson_path,
        output_path=result_file,
        format="geojson",
    )

    assert os.path.exists(result_file)
    gdf = gpd.read_file(result_file)
    assert len(gdf) > 0


def test_invalid_source(test_geojson_path):
    """Test handling of invalid source."""
    with pytest.raises(ValueError):
        download_buildings(
            source="invalid",
            input_path=test_geojson_path,
            output_path=os.path.join(OUTPUT_DIR, "invalid.geojson"),
            format="geojson",
        )


# def test_compare_results(test_geojson_path):
#     """Compare results from different sources."""
#     sources = {"google": None, "microsoft": "Nepal", "osm": None, "overture": None}

#     results = {}
#     for source, location in sources.items():
#         result_file = os.path.join(OUTPUT_DIR, f"{source}_buildings.geojson")
#         download_buildings(
#             source=source,
#             input_path=test_geojson_path,
#             output_path=result_file,
#             format="geojson",
#             location=location,
#         )
#         results[source] = gpd.read_file(result_file)

#     # Print comparison statistics
#     for source, gdf in results.items():
#         print(f"\n{source.upper()} Statistics:")
#         print(f"Number of buildings: {len(gdf)}")
#         print(f"Total area: {gdf.geometry.area.sum():.2f} square meters")
