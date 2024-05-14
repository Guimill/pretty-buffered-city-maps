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


# https://simplemaps.com/data/world-cities

import streamlit as st
from streamlit.logger import get_logger
import streamlit_folium as stf
import osmnx as ox

LOGGER = get_logger(__name__)

def run():
    st.set_page_config(
        page_title="Hello",
        page_icon="👋",
    )

    st.title('Paris')

    # Define a smaller bounding box for Paris
    bbox = (48.9, 2.3, 48.8, 2.4)  # Example smaller bounding box coordinates

    # Fetch waterway features within the bounding box using osmnx
    waterway_data = ox.geometries_from_bbox(bbox[0], bbox[1], bbox[2], bbox[3], tags={'waterway': True})

    # Create a Folium map centered on Paris with Stamen Toner background
    m = stf.folium.Map(location=[48.8566, 2.3522], zoom_start=12, tiles='Stamen Toner')

    # Add waterway features from osmnx to the map
    for index, row in waterway_data.iterrows():
        if row.geometry.geom_type == 'LineString':
            stf.folium.PolyLine(locations=row.geometry.coords, color='red').add_to(m)

    # Display the map
    stf.folium_static(m)

if __name__ == "__main__":
    run()
