import streamlit as st
from bs4 import BeautifulSoup
import re, requests
import pandas as pd
import io
from PIL import Image
import selenium
import streamlit_folium as stf
from map_utils import (create_map,fetch_map_data,add_elements_to_map)
from language import (
    Exemple_Dictionnary, Ville_Dictionnary, Tronçons_Dictionnary,
    Autoroutes_Dictionnary, Boulevards_Dictionnary, Haies_Dictionnary,
    Cours_d_eaux_Dictionnary, Littoral_Dictionnary
)

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
        waterways_on = st.checkbox(Cours_d_eaux_Dictionnary[Language_option], value = True)
    with col3:
        coastline_color = st.color_picker("", "#c0c0c0", key='coastline')
        coastline_on = st.checkbox(Littoral_Dictionnary[Language_option], value = True)
    with col4:
        roads_color = st.color_picker("", "#ffd700", key='trunk')
        trunk_on = st.checkbox(Tronçons_Dictionnary[Language_option], value = True)
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

#    url = "https://pretty-buffered-city-maps.streamlit.app/"

    # Send a GET request to the URL
#    response = requests.get(url)

    # Check if the request was successful (status code 200)
#    if response.status_code == 200:
        # Parse the HTML content using BeautifulSoup
#        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the SVG element by its ID or class
#        svg_element = soup.find('svg', id='your-svg-id')
        
#        if svg_element:
            # If the SVG element is found, you can print or manipulate it here
#            st.code(svg_element)
#            st.write(svg_element)
#        else:
#            st.write("SVG element not found.")
#    else:
#        st.write("Failed to fetch the page.")
    

#    svg_content = '''
#    <svg width="704" height="516.8" xmlns="http://www.w3.org/2000/svg">
#        <g>
#            <path class="leaflet-interactive" stroke="none" fill="white" fill-opacity="1" fill-rule="evenodd" d="M-150,255a500,500 0 1,0 1000,0 a500,500 0 1,0 -1000,0 "></path>
#            <path class="leaflet-interactive" stroke="none" fill="#0e1117" fill-opacity="1" fill-rule="evenodd" d="M100,255a250,250 0 1,0 500,0 a250,250 0 1,0 -500,0 "></path>
#        </g>
#    </svg>
#    '''

    # Convert SVG to PNG
#    cairosvg.svg2png(bytestring=svg_content.encode(), write_to="output.png")

    img_data = m._to_png(5)
    img = Image.open(io.BytesIO(img_data))
    img_path = 'image.png'
    img.save(img_path)
    
    # Offer the PNG image as a downloadable file using Streamlit
    st.download_button(label="Download PNG", data=img_path, file_name="image.png", mime="image/png")

    col_don_1, col_don_2, col_don_3 = st.columns([0.1, 0.8, 0.1])
    with col_don_1:
        st.text("")
    with col_don_2:
        st.link_button("Je ne vends pas les cartes, si vous voulez soutenir mon travail vous pouvez me faire un don :", "https://liberapay.com/SchwarzLowe")
    with col_don_3:
        st.text("")

if __name__ == "__main__":
    run()
