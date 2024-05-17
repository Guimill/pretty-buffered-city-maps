import streamlit as st
from streamlit.logger import get_logger
import streamlit_folium as stf
import re, requests
import pandas as pd

#### Languages ####

Exemple_Dictionnary = {
    "French"  : "Pour les villes avec un nom contenant des charactères spéciaux, concatenez les noms",
    "English" : "For cities with a name containing special characters, just write them as glued",
    "Chinese" : "对于名称中有特殊字符的城市，只需将其写成 并列 即可",
    "Italian" : "Per le città con un nuome contenente caratteri speciali, scrivetele attacato",
    "Spanish" : "Para las ciudades con un nombre que contengan caracteres especiales, escribalos pegados ...",
    "Breton"  : ""
}

Ville_Dictionnary = {
    "French"  : "Nommez une ville",
    "English" : "Name a city",
    "Chinese" : "命名一个城市",
    "Italian" : "Chiama una città",
    "Spanish" : "Escriba una ciudad",
    "Breton"  : ""
}

Tronçons_Dictionnary = {
    "French"  : "Tronçons",
    "English" : "Trunk",
    "Chinese" : "公路路段",
    "Italian" : "Tratti autostrade",
    "Spanish" : "Nombre autopista",
    "Breton"  : ""
}

Autoroutes_Dictionnary = {
    "French"  : "Autoroutes",
    "English" : "Motorways",
    "Chinese" : "高速公路",
    "Italian" : "Autostrade",
    "Spanish" : "Autopista",
    "Breton"  : ""
}

Boulevards_Dictionnary = {
    "French"  : "Boulevards",
    "English" : "Boulevards",
    "Chinese" : "林荫大道",
    "Italian" : "Viali",
    "Spanish" : "Boulevards",
    "Breton"  : ""
}

Haies_Dictionnary = {
    "French"  : "Haies",
    "English" : "Tree rows",
    "Chinese" : "树篱",
    "Italian" : "Siepi",
    "Spanish" : "Senderos",
    "Breton"  : ""
}

Cours_d_eaux_Dictionnary = {
    "French"  : "Cours d'eau",
    "English" : "Rivers",
    "Chinese" : "川",
    "Italian" : "Fiumi",
    "Spanish" : "Rios",
    "Breton"  : ""
}

Littoral_Dictionnary = {
    "French"  : "Littoral",
    "English" : "Coastlines",
    "Chinese" : "岸线",
    "Italian" : "Costa",
    "Spanish" : "Costa",
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

    col_language_1, col_language_2, col_language_3, col_language_4 = st.columns(4)
    with col_language_1:
        st.text("")
    with col_language_2:
        st.text("")
    with col_language_3:
        st.text("")
    with col_language_4:
        Language_option = st.selectbox("",("French", "English", "Chinese","Italian","Spanish","Breton"))

    st.write("# Beautiful Map Designer !")

    st.markdown(f""" {Exemple_Dictionnary[Language_option]}.
                
                Aix-en-Provence -> aixenprovence
                """)

    citie_selector = st.text_input(f'{Ville_Dictionnary[Language_option]}', 'Angers')
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

    m = stf.folium.Map(location=[city_lat, city_lng], zoom_start=10, no_touch=True, zoom_control=False,    dragging=False,  scrollWheelZoom=False)

    

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
    col1, col2, col3, col4, col5, col6 = st.columns([0.1, 0.2, 0.2, 0.2, 0.2, 0.1])
    with col1:
        st.write("")
    with col2:
        waterways_color = st.color_picker("", "#00ffff", key='waterways')
        waterways_on = st.checkbox(Cours_d_eaux_Dictionnary[Language_option], value=True)
    with col3:
        coastline_color = st.color_picker("", "#c0c0c0", key='coastline')
        coastline_on = st.checkbox(Littoral_Dictionnary[Language_option], value=True)
    with col4:
        roads_color = st.color_picker("", "#ffd700", key='trunk')
        trunk_on = st.checkbox(Tronçons_Dictionnary[Language_option], value=True)
        motorway_on = st.checkbox(Autoroutes_Dictionnary[Language_option])
        primary_on = st.checkbox(Boulevards_Dictionnary[Language_option])
    with col5:
        tree_color = st.color_picker("", "#00a67d", key='tree')
        tree_on = st.checkbox(Haies_Dictionnary[Language_option])
    with col6:
        st.write("")

    st.text("")
    st.text("")
    st.text("")
    st.text("")
    st.text("")


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


    stf.folium_static(m,width=700, height=500)
    
    map_file = "map.html"
    m.save(map_file)

    # Read the HTML file content
    with open(map_file, "r") as file:
        map_html = file.read()

    # Create a download button
    st.download_button(
        label="Download map",
        data=map_html,
        file_name=map_file,
        mime="text/html"
    )

    st.text("")
    st.text("")
    st.text("")
    st.text("")

    col_don_1, col_don_2, col_don_3 = st.columns([0.1, 0.8, 0.1])
    with col_don_1:
        st.text("")
    with col_don_2:
        st.link_button("Je ne vends pas les cartes, si vous voulez soutenir mon travail vous pouvez me faire un don :", "https://liberapay.com/SchwarzLowe")
    with col_don_3:
        st.text("")


if __name__ == "__main__":
    run()
