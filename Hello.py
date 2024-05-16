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
        way["highway"="trunk"](around:30000, {city_lat}, {city_lng});
        way["highway"="motorway"](around:30000, {city_lat}, {city_lng});
        way["highway"="primary"](around:30000, {city_lat}, {city_lng});
        way["waterway"="river"](around:20000, {city_lat}, {city_lng});
        way["natural"="tree_row"](around:10000, {city_lat}, {city_lng});
        way["natural"="coastline"](around:100000, {city_lat}, {city_lng});
        );
        out geom;
    """

    response = requests.get(overpass_url, params={'data': overpass_query})
    data = response.json()

    m = stf.folium.Map(location=[city_lat, city_lng], zoom_start=10)

    radius = 500
    stf.folium.CircleMarker(
        location=[city_lat, city_lng],
        radius=radius,
        color="white",
        stroke=False,
        fill=True,
        fill_opacity=1,
        ).add_to(m)


    stf.folium.CircleMarker(
        location=[city_lat, city_lng],
        radius=radius - 250,
        color="#0e1117",
        stroke=False,
        fill=True,
        fill_opacity=1,
        ).add_to(m)

# Create columns for checkboxes and color pickers
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        waterways_color = st.color_picker("", "#00ffff", key='waterways')
        waterways_on = st.checkbox("Cours d'eaux", value=True)
    with col2:
        coastline_color = st.color_picker("", "#c0c0c0", key='coastline')
        coastline_on = st.checkbox("Côtes", value=True)
    with col3:
        roads_color = st.color_picker("", "#ffd700", key='trunk')
        trunk_on = st.checkbox("Tronçons", value=True)
        motorway_on = st.checkbox("Autoroutes")
        primary_on = st.checkbox("Boulevards")
    with col4:
        tree_color = st.color_picker("", "#00a67d", key='tree')
        tree_on = st.checkbox("Haies")



    for element in data['elements']:
        if 'geometry' in element:
            coordinates = [(node['lat'], node['lon']) for node in element['geometry']]
            highway_type = element['tags'].get('highway')
            natural_type = element['tags'].get('natural')
            waterway_type = element['tags'].get('waterway')

            if waterways_on and waterway_type == 'river':
                stf.folium.PolyLine(locations=coordinates, color=waterways_color).add_to(m)
            elif trunk_on and highway_type == 'trunk':
                stf.folium.PolyLine(locations=coordinates, color=roads_color).add_to(m)
            elif motorway_on and highway_type == 'motorway':
                stf.folium.PolyLine(locations=coordinates, color=roads_color).add_to(m)
            elif primary_on and highway_type == 'primary':
                stf.folium.PolyLine(locations=coordinates, color=roads_color).add_to(m)
            elif coastline_on and natural_type == 'coastline':
                stf.folium.PolyLine(locations=coordinates, color=coastline_color).add_to(m)
            elif tree_on and natural_type == 'tree_row':
                stf.folium.PolyLine(locations=coordinates, color=tree_color).add_to(m)

    # Render the folium map in Streamlit
    stf.folium_static(m)


if __name__ == "__main__":
    run()
