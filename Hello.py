# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


#https://simplemaps.com/data/world-cities

import streamlit as st
from streamlit.logger import get_logger
import streamlit_folium as stf
import pandas as pd
import re
import requests
import json
import osmnx as ox

LOGGER = get_logger(__name__)

def run():
    st.set_page_config(
        page_title="Hello",
        page_icon="👋",
    )
    st.title('Paris River Lines and Wetlands Map')

    # Specify the location (Paris) and the feature types (rivers and wetlands)
    location = "Paris, France"
    feature_types = ["river", "wetland"]

    # Retrieve river lines and wetlands data using osmnx
    data = ox.geometries_from_place(location, tags={'waterway': '|'.join(feature_types)})

    # Create a Folium map centered on Paris with Stamen Toner background
    m = stf.folium.Map(location=[48.8566, 2.3522], zoom_start=12, tiles='Stamen Toner')

    # Add river lines and wetlands to the map
    for index, row in data.iterrows():
        if row.geometry.type == 'LineString':
            stf.folium.PolyLine(locations=row.geometry.coords, color='blue').add_to(m)
        elif row.geometry.type == 'Polygon':
            stf.folium.Polygon(locations=row.geometry.exterior.coords, color='green', fill=True, fill_color='green').add_to(m)

    # Add a circular crop with radius 100 pixels
    crop_center = [48.8566, 2.3522]  # Center of Paris
    crop_radius = 100  # Radius in pixels
    stf.folium.CircleMarker(location=crop_center, radius=crop_radius, color='black', fill=True, fill_opacity=0.5).add_to(m)

    # Display the map using Streamlit
    stf.folium_static(m)

if __name__ == "__main__":
    run()
