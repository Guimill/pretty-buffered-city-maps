import re
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from language import (
    Autoroutes_Dictionnary,
    Boulevards_Dictionnary,
    Cours_d_eaux_Dictionnary,
    Exemple_Dictionnary,
    Haies_Dictionnary,
    Introuvable_Dictionnary,
    Littoral_Dictionnary,
    Tronçons_Dictionnary,
    Ville_Dictionnary,
)
from map_utils import MapDataError, add_elements_to_map, create_map, fetch_map_data, render_png

DATA_FILE = Path(__file__).parent / "data" / "worldcities.csv"


def normalize(name):
    """'Aix-en-Provence', 'aix en provence' and 'aixenprovence' all give 'aixenprovence'."""
    name = unicodedata.normalize("NFKD", str(name))
    name = "".join(c for c in name if not unicodedata.combining(c))
    return re.sub(r"[\W_]", "", name).lower()


@st.cache_data
def load_cities():
    cities = pd.read_csv(DATA_FILE)
    cities["key"] = cities["city"].map(normalize)
    cities["key_ascii"] = cities["city_ascii"].map(normalize)
    return cities


def find_city(cities, query):
    key = normalize(query)
    if not key:
        return cities.iloc[0:0]
    # The CSV is sorted by population, so the biggest match comes first.
    return cities[(cities["key"] == key) | (cities["key_ascii"] == key)]


def run():
    st.set_page_config(page_title="Beautiful Map Designer", page_icon="🗺️")

    _, _, _, col_language = st.columns(4)
    with col_language:
        language = st.selectbox(
            "Language",
            ("French", "English", "Chinese", "Italian", "Spanish", "Breton"),
            label_visibility="collapsed",
        )

    st.write("# Beautiful Map Designer !")
    st.markdown(f"""{Exemple_Dictionnary[language]}.

    Aix-en-Provence -> aixenprovence
    """)

    cities = load_cities()
    city_query = st.text_input(Ville_Dictionnary[language], "Angers")
    matches = find_city(cities, city_query)
    if matches.empty:
        st.error(f"{Introuvable_Dictionnary[language]} : {city_query}")
        st.stop()

    if len(matches) > 1:
        labels = [f"{r.city}, {r.admin_name}, {r.country}" for r in matches.itertuples()]
        choice = st.selectbox(" ", range(len(labels)), format_func=labels.__getitem__,
                              label_visibility="collapsed")
        city = matches.iloc[choice]
    else:
        city = matches.iloc[0]
    city_lat, city_lng = float(city["lat"]), float(city["lng"])

    _, col2, col3, col4, col5, _ = st.columns([0.1, 0.2, 0.2, 0.2, 0.2, 0.1])
    with col2:
        waterways_color = st.color_picker("waterways", "#00ffff", key="waterways",
                                          label_visibility="collapsed")
        waterways_on = st.checkbox(Cours_d_eaux_Dictionnary[language], value=True)
    with col3:
        coastline_color = st.color_picker("coastline", "#c0c0c0", key="coastline",
                                          label_visibility="collapsed")
        coastline_on = st.checkbox(Littoral_Dictionnary[language], value=True)
    with col4:
        roads_color = st.color_picker("roads", "#ffd700", key="trunk",
                                      label_visibility="collapsed")
        trunk_on = st.checkbox(Tronçons_Dictionnary[language], value=True)
        motorway_on = st.checkbox(Autoroutes_Dictionnary[language])
        primary_on = st.checkbox(Boulevards_Dictionnary[language])
    with col5:
        tree_color = st.color_picker("trees", "#00a67d", key="tree",
                                     label_visibility="collapsed")
        tree_on = st.checkbox(Haies_Dictionnary[language])

    st.write("")

    try:
        with st.spinner("OpenStreetMap…"):
            data = fetch_map_data(city_lat, city_lng)
    except MapDataError as exc:
        st.error(str(exc))
        st.stop()

    colors = {
        "waterways": waterways_color,
        "coastline": coastline_color,
        "trunk": roads_color,
        "tree": tree_color,
    }
    options = {
        "waterways_on": waterways_on,
        "coastline_on": coastline_on,
        "trunk_on": trunk_on,
        "motorway_on": motorway_on,
        "primary_on": primary_on,
        "tree_on": tree_on,
    }

    m = create_map(city_lat, city_lng)
    m = add_elements_to_map(data, m, colors, options)
    st_folium(m, width=700, height=600, returned_objects=[], key="map")

    png = render_png(data, city_lat, city_lng, colors, options)

    _, col_don, _ = st.columns([0.1, 0.8, 0.1])
    with col_don:
        st.download_button(
            label="Download PNG",
            data=png,
            file_name=f"{normalize(city['city_ascii'])}_map.png",
            mime="image/png",
        )
        st.link_button(
            "Je ne vends pas les cartes, si vous voulez soutenir mon travail vous pouvez me faire un don :",
            "https://liberapay.com/SchwarzLowe",
        )


if __name__ == "__main__":
    run()
