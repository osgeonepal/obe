# OBE (Open Buildings Extractor)

A Python package to extract building footprints from multiple open data sources including Google Open Buildings, Microsoft Building Footprints, OpenStreetMap, and Overture Maps.

## Example 
Run Example Notebook [here:](./example_obe_usage.ipynb) 

## Features

- Extract building footprints from multiple sources:
  - **Google** Open Buildings
  - **Microsoft** Building Footprints
  - **OpenStreetMap**
  - **Overture** Maps
- Support for multiple output formats:
  - GeoJSON
  - GeoPackage
  - Shapefile
  - GeoJSONSeq
  - GeoParquet
- Command-line 
- Python API
- [Streamlit web interface](https://obextract.streamlit.app/)

## Installation

Using pip:
```bash
pip install obe
```

Using poetry 
```bash
poetry add obe
```

## Usage 

### Command line interface 

```bash
obe --source <source> --input <input.geojson> --output <output.geojson>
```


### Examples:
```bash
# Google Open Buildings
obe --source google --input area.geojson --output google_buildings.geojson

# Microsoft Building Footprints (requires location)
obe --source microsoft --input area.geojson --output ms_buildings.geojson --location Nepal

# OpenStreetMap
obe --source osm --input area.geojson --output osm_buildings.geojson

# Overture Maps
obe --source overture --input area.geojson --output overture_buildings.geojson
```

### Python API

```python
from obe.app import download_buildings

# Download buildings from any source
download_buildings(
    source="google",  # or "microsoft", "osm", "overture"
    input_path="area.geojson",
    output_path="buildings.geojson",
    format="geojson",  # or "geopackage", "shapefile", "geojsonseq", "geoparquet"
    location=None  # required for Microsoft ("Nepal", "India", etc.)
)
```

### Example Input 
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {},
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [83.96184435207743, 28.212767538129086],
            [83.96184435207743, 28.20236573207498],
            [83.97605449676462, 28.20236573207498],
            [83.97605449676462, 28.212767538129086],
            [83.96184435207743, 28.212767538129086]
          ]
        ]
      }
    }
  ]
}
```

### Example Output 

![image](https://github.com/user-attachments/assets/a7646d95-f80d-49ed-afc9-1189055ea890)

### Authors 
- Initiated by @kshitijrajsharma 
