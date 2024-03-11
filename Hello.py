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

LOGGER = get_logger(__name__)

Cities = pd.read_csv('data/worldcities.csv')
def remove_special_chars(city):
    pattern = r'[^\w\s]'
    return re.sub(pattern, '', city)

Cities['city'] = Cities['city'].apply(remove_special_chars)
Cities['city'] = Cities['city'].str.lower()

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



    m = stf.folium.Map(location=[city_lat, city_lng], zoom_start=9)

    radius = 100
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
