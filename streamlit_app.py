import io
import os
from pathlib import Path

import geopandas as gpd
import pydeck as pdk
import streamlit as st

from src.obe.app import download_buildings


def calculate_area_sqkm(gdf):
    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)
    gdf_projected = gdf.to_crs(epsg=3857)
    area_sqkm = gdf_projected.geometry.area.sum() / 1e6
    return area_sqkm


st.set_page_config(
    page_title="Open Buildings Extractor",
    page_icon="🏘️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main { padding: 20px; }
    .stButton>button { width: 100%; }
    .reportview-container .main .block-container { padding-top: 2rem; }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("Open Buildings Extractor")
st.markdown("*Extract building footprints from various open data sources*")

with st.sidebar:
    st.header("Configuration")

    data_sources = {
        "google": "Google Open Buildings",
        "microsoft": "Microsoft Buildings",
        "osm": "OpenStreetMap Buildings",
        "overture": "Overture Maps Buildings",
    }

    file_formats = {
        "geojson": "GeoJSON (.geojson)",
        "geojsonseq": "GeoJSON Sequence (.geojsonseq)",
        "geoparquet": "GeoParquet (.parquet)",
        "geopackage": "GeoPackage (.gpkg)",
        "shapefile": "Shapefile (.shp)",
    }

    source = st.selectbox(
        "Select Data Source",
        options=list(data_sources.keys()),
        format_func=lambda x: data_sources[x],
    )

    file_format = st.selectbox(
        "Select Output Format",
        options=list(file_formats.keys()),
        format_func=lambda x: file_formats[x],
    )

    location = (
        st.text_input(
            "Country Name",
            placeholder="e.g. United States",
            help="Required for Microsoft Buildings API",
        )
        if source == "microsoft"
        else ""
    )

tabs = st.tabs(["Input", "Results"])

with tabs[0]:
    st.subheader("Provide Area of Interest")
    input_col1, input_col2 = st.columns(2)

    with input_col1:
        input_option = st.radio("Choose Input Method", ["Upload File", "Paste GeoJSON"])

    with input_col2:
        if input_option == "Upload File":
            uploaded_file = st.file_uploader(
                "Upload GeoJSON or GeoParquet file", type=["geojson", "parquet"]
            )
        else:
            geojson_input = st.text_area(
                "Paste GeoJSON content",
                height=200,
                placeholder='{"type": "FeatureCollection", ...}',
            )

with tabs[1]:
    col1, col2 = st.columns([2, 1])

    with col1:
        try:
            if input_option == "Upload File" and uploaded_file is not None:
                gdf = (
                    gpd.read_file(io.BytesIO(uploaded_file.getvalue()))
                    if uploaded_file.name.endswith(".geojson")
                    else gpd.read_parquet(io.BytesIO(uploaded_file.getvalue()))
                )
            elif input_option == "Paste GeoJSON" and geojson_input:
                gdf = gpd.GeoDataFrame.from_features(
                    eval(geojson_input), crs="EPSG:4326"
                )

            if "gdf" in locals():
                area_sqkm = calculate_area_sqkm(gdf)
                bbox = gdf.total_bounds
                view_state = pdk.ViewState(
                    longitude=(bbox[0] + bbox[2]) / 2,
                    latitude=(bbox[1] + bbox[3]) / 2,
                    zoom=10,
                    pitch=0,
                )

                layer = pdk.Layer(
                    "GeoJsonLayer",
                    data=gdf.__geo_interface__,
                    opacity=0.8,
                    stroked=True,
                    filled=True,
                    extruded=False,
                    get_fill_color=[0, 100, 200, 140],
                    get_line_color=[0, 0, 0, 200],
                    get_line_width=2,
                    pickable=True,
                )

                map_plot = pdk.Deck(
                    layers=[layer],
                    initial_view_state=view_state,
                    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                )

                map_container = st.pydeck_chart(map_plot)

                if area_sqkm > 5000:
                    st.error(
                        "❌ Input area exceeds 5000 km². Please provide a smaller area."
                    )

        except Exception as e:
            st.info("Upload data or paste GeoJSON to see the preview")

    with col2:
        if "gdf" in locals():
            st.subheader("Area Statistics")
            st.metric("Number of Features", len(gdf))
            st.metric("Area", f"{area_sqkm:.2f} km²")

            if area_sqkm <= 5000:
                if st.button(
                    "🏗️ Extract Buildings", type="primary", use_container_width=True
                ):
                    with st.spinner("Downloading building footprints..."):
                        try:
                            temp_dir = Path("temp")
                            temp_dir.mkdir(exist_ok=True)

                            input_path = temp_dir / "input.geojson"
                            output_path = temp_dir / f"buildings_{source}.{file_format}"

                            with open(
                                input_path,
                                "w" if input_option == "Paste GeoJSON" else "wb",
                            ) as f:
                                f.write(
                                    geojson_input
                                    if input_option == "Paste GeoJSON"
                                    else uploaded_file.getvalue()
                                )

                            download_buildings(
                                source,
                                str(input_path),
                                str(output_path),
                                file_format,
                                location,
                            )

                            file_size = os.path.getsize(output_path)
                            file_size_mb = file_size / (1024 * 1024)

                            st.success("✨ Buildings extracted successfully!")
                            st.info(
                                f"📁 Output file: {output_path.name} ({file_size_mb:.2f} MB)"
                            )

                            if file_format == "geojson":
                                output_gdf = gpd.read_file(output_path)
                                buildings_layer = pdk.Layer(
                                    "GeoJsonLayer",
                                    data=output_gdf.__geo_interface__,
                                    opacity=0.8,
                                    stroked=True,
                                    filled=True,
                                    extruded=False,
                                    get_fill_color=[200, 30, 0, 140],
                                    get_line_color=[0, 0, 0, 200],
                                    get_line_width=1,
                                    pickable=True,
                                )

                                map_plot.layers.append(buildings_layer)
                                map_container.pydeck_chart(map_plot)
                                st.metric("Buildings found", len(output_gdf))

                            with open(output_path, "rb") as f:
                                st.download_button(
                                    label=f"📥 Download {file_formats[file_format]}",
                                    data=f.read(),
                                    file_name=output_path.name,
                                    mime=f"application/{file_format}",
                                    use_container_width=True,
                                )

                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                            st.error("Please check your input data and try again.")
        else:
            st.info("Statistics will appear here once data is loaded")

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>Made with ❤️ by Kshitij | 
        <a href="https://github.com/kshitijrajsharma/obe">GitHub</a></p>
    </div>
""",
    unsafe_allow_html=True,
)
