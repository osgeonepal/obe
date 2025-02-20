import io
import os

import geopandas as gpd
import streamlit as st

from src.obe.app import download_buildings

st.title("Open Buildings Extractor")

data_sources = ["google", "microsoft", "osm", "overture"]
file_formats = ["geojson", "geojsonseq", "geoparquet", "geopackage", "shapefile"]

input_option = st.sidebar.radio("Input Option", ["Paste GeoJSON", "Upload File"])
source = st.sidebar.selectbox("Data Source", data_sources)
file_format = st.sidebar.selectbox("File Format", file_formats)
location = st.sidebar.text_input("Location (required for Microsoft)", value="")

if input_option == "Paste GeoJSON":
    geojson_input = st.text_area("Paste GeoJSON")
    if geojson_input:
        gdf = gpd.GeoDataFrame.from_features(eval(geojson_input))
        bbox = gdf.total_bounds
        st.write(f"Calculated Bounding Box: {bbox}")
elif input_option == "Upload File":
    uploaded_file = st.file_uploader("Choose a File")
    if uploaded_file is not None:
        if uploaded_file.name.endswith(".geojson"):
            gdf = gpd.read_file(io.BytesIO(uploaded_file.getvalue()))
        elif uploaded_file.name.endswith(".parquet"):
            gdf = gpd.read_parquet(io.BytesIO(uploaded_file.getvalue()))
        else:
            st.error("Invalid file format. Please upload a GeoJSON or GeoParquet file.")
        bbox = gdf.total_bounds
        st.write(f"Calculated Bounding Box: {bbox}")

if st.button("Download Data"):
    with st.spinner("Downloading data..."):
        input_path = "input.geojson"
        output_path = f"output_{source}_buildings.{file_format}"

        if input_option == "Paste GeoJSON":
            with open(input_path, "w") as f:
                f.write(geojson_input)
        elif input_option == "Upload File" and uploaded_file is not None:
            with open(input_path, "wb") as f:
                f.write(uploaded_file.getvalue())

        try:
            download_buildings(
                source,
                input_path,
                output_path,
                file_format,
                location,
            )
            st.success("Data downloaded successfully!")
            file_size = os.path.getsize(output_path)
            file_size_mb = file_size / (1024 * 1024)
            file_size_str = f"{file_size_mb:.2f} MB"
            file_info = f"{output_path} ({file_size_str})"

            st.download_button(
                label=file_info,
                data=open(output_path, "rb").read(),
                file_name=output_path,
                mime=f"application/{file_format}",
            )
        except Exception as e:
            st.error(f"Error downloading data: {e}")
