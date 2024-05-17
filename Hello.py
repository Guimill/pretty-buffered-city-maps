import streamlit as st
from streamlit.logger import get_logger
import streamlit_folium as stf
import re, requests
import pandas as pd

#### Languages ####

Exemple_Dictionnary = {
    "French"  : "Pour les villes avec un nom contenant des charactères spéciaux, concatenez les noms",
    "English" : "For cities with a name containing special characters, just write them as glued",
    "Chinese" : "",
    "Italian" : "Per le città con un nuome contenente caratteri speciali, scrivetele attacato",
    "Spanish" : "Por ciudad con un llama ...",
    "Breton"  : ""
}

Ville_Dictionnary = {
    "French"  : "Nommez une ville",
    "English" : "Name a city",
    "Chinese" : "命名一个城市",
    "Italian" : "Chiamare una città",
    "Spanish" : "Llamar una ciudad",
    "Breton"  : ""
}

Tronçons_Dictionnary = {
    "French"  : "Tronçons",
    "English" : "Trunk",
    "Chinese" : "公路路段",
    "Italian" : "Tratti autostrade",
    "Spanish" : "",
    "Breton"  : ""
}

Autoroutes_Dictionnary = {
    "French"  : "Autoroutes",
    "English" : "Motorways",
    "Chinese" : "高速公路",
    "Italian" : "Autostrade",
    "Spanish" : "",
    "Breton"  : ""
}

Boulevards_Dictionnary = {
    "French"  : "Boulevards",
    "English" : "Boulevards",
    "Chinese" : "林荫大道",
    "Italian" : "Viali",
    "Spanish" : "",
    "Breton"  : ""
}

Haies_Dictionnary = {
    "French"  : "Haies",
    "English" : "Tree rows",
    "Chinese" : "树篱",
    "Italian" : "Ostacoli",
    "Spanish" : "",
    "Breton"  : ""
}

Cours_d_eaux_Dictionnary = {
    "French"  : "Cours d'eau",
    "English" : "Rivers",
    "Chinese" : "川",
    "Italian" : "Fiumi",
    "Spanish" : "",
    "Breton"  : ""
}

Littoral_Dictionnary = {
    "French"  : "Littoral",
    "English" : "Coastlines",
    "Chinese" : "",
    "Italian" : "",
    "Spanish" : "",
    "Breton"  : ""
}


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

    Language_option = st.selectbox("Languages :",("English", "French", "Chinese","Italian","Spanish","Breton"))

    st.write("# Beautiful Map Designer !")

    st.markdown(f""" {Exemple_Dictionnary[Language_option]}.
                
                example : Aix-en-Provence -> aixenprovence
                """)

    citie_selector = st.text_input(f'{Ville_Dictionnary[Language_option]}', 'Paris')
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
        way["highway"="trunk"](around:50000, {city_lat}, {city_lng});
        way["highway"="motorway"](around:50000, {city_lat}, {city_lng});
        way["highway"="primary"](around:20000, {city_lat}, {city_lng});
        way["waterway"="river"](around:20000, {city_lat}, {city_lng});
        way["natural"="tree_row"](around:30000, {city_lat}, {city_lng});
        way["natural"="coastline"](around:100000, {city_lat}, {city_lng});
        );
        out geom;
    """

    response = requests.get(overpass_url, params={'data': overpass_query})
    data = response.json()

    m = stf.folium.Map(location=[city_lat, city_lng], zoom_start=10, no_touch=True)

    

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
        waterways_on = st.checkbox(Cours_d_eaux_Dictionnary[Language_option], value=True)
    with col2:
        coastline_color = st.color_picker("", "#c0c0c0", key='coastline')
        coastline_on = st.checkbox(Littoral_Dictionnary[Language_option], value=True)
    with col3:
        roads_color = st.color_picker("", "#ffd700", key='trunk')
        trunk_on = st.checkbox(Tronçons_Dictionnary[Language_option], value=True)
        motorway_on = st.checkbox(Autoroutes_Dictionnary[Language_option])
        primary_on = st.checkbox(Boulevards_Dictionnary[Language_option])
    with col4:
        tree_color = st.color_picker("", "#00a67d", key='tree')
        tree_on = st.checkbox(Haies_Dictionnary[Language_option])



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
