import streamlit as st
from streamlit.logger import get_logger
import streamlit_folium as stf
import osmnx as ox
import re, requests
import pandas as pd

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

    overpass_url = "http://overpass-api.de/api/interpreter"  # Replace with the appropriate Overpass API endpoint

    overpass_query = f"""
        [out:json];
        (
        relation["waterway"="river"](48.8156,2.2241,48.9021,2.4699);
        relation["highway"="primary"](48.8156,2.2241,48.9021,2.4699);
        );
        out geom;
    """

    response = requests.get(overpass_url, params={'data': overpass_query})
    data = response.json()

    m = stf.folium.Map(location=[city_lat, city_lng], zoom_start=10)

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

    if 'elements' in data:
            for element in data['elements']:
                if 'geometry' in element:
                    if 'type' in element['geometry'] and element['geometry']['type'] == 'LineString':
                        coordinates = element['geometry']['coordinates']
                        stf.folium.PolyLine(locations=coordinates, color='red').add_to(m)


    stf.folium_static(m)


if __name__ == "__main__":
    run()
