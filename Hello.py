import streamlit as st
from streamlit.logger import get_logger
import streamlit_folium as stf
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
        way["highway"="trunk"](around:20000, {city_lat}, {city_lng});
        way["highway"="motorway"](around:20000, {city_lat}, {city_lng});
        relation["waterway"="river"](around:10000, {city_lat}, {city_lng});
        way["natural"="tree_row"](around:10000, {city_lat}, {city_lng});
        way["natural"="coastline"](around:20000, {city_lat}, {city_lng});
        );
        out geom;
    """

    response = requests.get(overpass_url, params={'data': overpass_query})
    if response.status_code == 200:
        data = response.json()
        st.write("Data retrieved successfully!")
    else:
        st.write("Failed to retrieve data. Status code:", response.status_code)
        st.write(response.text)  # Print the response content for further inspection

    m = stf.folium.Map(location=[city_lat, city_lng], zoom_start=10)

    radius = 5000
    stf.folium.CircleMarker(
        location=[city_lat, city_lng],
        radius=radius,
        color="black",
        stroke=False,
        fill=True,
        fill_opacity=1,
        ).add_to(m)


    if 'elements' in data:
        for element in data['elements']:
            if element['type'] == 'relation' and 'members' in element:
                # Process river lines
                for member in element['members']:
                    if member['type'] == 'way' and 'geometry' in member:
                        coordinates = [(node['lat'], node['lon']) for node in member['geometry']]
                        stf.folium.PolyLine(locations=coordinates, color='cyan').add_to(m)
            if element['type'] == 'way' and 'tags' in element and element['tags'].get('highway') == 'trunk':
                # Process primary highways
                if 'geometry' in element:
                    coordinates = [(node['lat'], node['lon']) for node in element['geometry']]
                    stf.folium.PolyLine(locations=coordinates, color='gold').add_to(m)
            if element['type'] == 'way' and 'tags' in element and element['tags'].get('highway') == 'motorway':
                # Process primary highways
                if 'geometry' in element:
                    coordinates = [(node['lat'], node['lon']) for node in element['geometry']]
                    stf.folium.PolyLine(locations=coordinates, color='gold').add_to(m)
            if element['type'] == 'way' and 'tags' in element and element['tags'].get('natural') == 'coastline':
                # Process primary highways
                if 'geometry' in element:
                    coordinates = [(node['lat'], node['lon']) for node in element['geometry']]
                    stf.folium.PolyLine(locations=coordinates, color='silver').add_to(m)


    stf.folium_static(m)


if __name__ == "__main__":
    run()
