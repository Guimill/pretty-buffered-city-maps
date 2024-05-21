import streamlit as st
import re
import base64
import pandas as pd
import tempfile
from PIL import Image, ImageDraw
import streamlit_folium as stf
from language import (
    Exemple_Dictionnary, Ville_Dictionnary, Tronçons_Dictionnary,
    Autoroutes_Dictionnary, Boulevards_Dictionnary, Haies_Dictionnary,
    Cours_d_eaux_Dictionnary, Littoral_Dictionnary
)
from map_utils import create_map, add_elements_to_map, fetch_map_data

# Load the cities data
Cities = pd.read_csv('data/worldcities.csv')

def remove_special_chars(city):
    pattern = r'[^\w\s]'
    return re.sub(pattern, '', city)

Cities['city'] = Cities['city'].apply(remove_special_chars)
Cities['city'] = Cities['city'].str.lower()

def run():
    st.set_page_config(
        page_title="Beautiful Map Designer",
        page_icon="🗺️",
    )

    col_language_1, col_language_2, col_language_3, col_language_4 = st.columns(4)
    with col_language_1:
        st.text("")
    with col_language_2:
        st.text("")
    with col_language_3:
        st.text("")
    with col_language_4:
        Language_option = st.selectbox("", ("French", "English", "Chinese", "Italian", "Spanish", "Breton"))

    st.write("# Beautiful Map Designer !")

    st.markdown(f""" {Exemple_Dictionnary[Language_option]}.
                
                Aix-en-Provence -> aixenprovence
                """)

    citie_selector = st.text_input(f'{Ville_Dictionnary[Language_option]}', 'Angers')
    citie_selector = str.lower(citie_selector)
    city_lat = Cities.loc[Cities['city'] == citie_selector, 'lat'].iloc[0]
    city_lng = Cities.loc[Cities['city'] == citie_selector, 'lng'].iloc[0]

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

    data = fetch_map_data(city_lat, city_lng)
    
    colors = {
        'waterways': waterways_color,
        'coastline': coastline_color,
        'trunk': roads_color,
        'tree': tree_color
    }
    
    options = {
        'waterways_on': waterways_on,
        'coastline_on': coastline_on,
        'trunk_on': trunk_on,
        'motorway_on': motorway_on,
        'primary_on': primary_on,
        'tree_on': tree_on
    }

    m = create_map(city_lat, city_lng)
    m = add_elements_to_map(data, m, colors, options)
    stf.folium_static(m)

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
