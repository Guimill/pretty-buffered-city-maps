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

LOGGER = get_logger(__name__)

Cities = pd.read_csv('data/worldcities.csv')
def remove_special_chars(city):
    pattern = r'[^\w\s]'
    return re.sub(pattern, '', city)

Cities['city'] = Cities['city'].apply(remove_special_chars)
Cities['city'] = Cities['city'].str.lower()

overpass_url = "https://overpass-api.de/api/"

def run():
    st.set_page_config(
        page_title="Hello",
        page_icon="👋",
    )

    st.write("# Welcome to Paris!")

    st.markdown(""" For cities with a name containing special characters, just write them as glued.
                
                example : Aix-en-Provence -> aixenprovence
                """)

    citie_selector = st.text_input('Name a city !', 'Paris')
    citie_selector = str.lower(citie_selector)
    city_lat = Cities.loc[Cities['city'] == citie_selector, 'lat'].iloc[0]
    city_lng = Cities.loc[Cities['city'] == citie_selector, 'lng'].iloc[0]

    radius = 0.01  # 1 degree is approximately 111 kilometers

    # Calculate bounding box coordinates
    min_lat = city_lat - radius
    max_lat = city_lat + radius
    min_lng = city_lng - radius
    max_lng = city_lng + radius

    # Bounding box format: (min_lat, min_lng, max_lat, max_lng)
    bbox = (min_lat, min_lng, max_lat, max_lng)

    overpass_query = f"""
        [out:json];
        (
        way["highway"="cycleway"]({bbox});
        way["highway"="primary"]({bbox});
        way["highway"="motorway"]({bbox});
        way["building"="historic"]({bbox});
        way["waterway"="river"]({bbox});
        way["natural"="wetland"]({bbox});
        way["natural"="water"]({bbox});
        relation["waterway"="river"]({bbox});
        relation["natural"="wetland"]({bbox});
        relation["natural"="water"]({bbox});
        );
        (._;);
        out geom;
        >;
        out skel qt;
    """

    response = requests.get(overpass_url, params={'data': overpass_query})

    m = stf.folium.Map(location=[city_lat, city_lng], zoom_start=15)

    radius = 50
    stf.folium.CircleMarker(
        location=[city_lat, city_lng],
        radius=radius,
        color="cornflowerblue",
        stroke=False,
        fill=True,
        fill_opacity=0.6,
        opacity=1,
        popup="{} pixels".format(radius),
        tooltip="I am in pixels",
        ).add_to(m)

    stf.folium_static(m)


if __name__ == "__main__":
    run()


