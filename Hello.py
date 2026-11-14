import re
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st

from language import (
    Autoroutes_Dictionnary,
    Boulevards_Dictionnary,
    Cours_d_eaux_Dictionnary,
    Epaisseur_Dictionnary,
    Exemple_Dictionnary,
    Haies_Dictionnary,
    Introuvable_Dictionnary,
    Littoral_Dictionnary,
    Tronçons_Dictionnary,
    Ville_Dictionnary,
)
from map_utils import DEFAULT_LINE_WIDTH, MapDataError, get_layers, render_png

DATA_FILE = Path(__file__).parent / "data" / "worldcities.csv"

# Slider range for the line width (points on the 1200 px image)
MIN_WIDTH, MAX_WIDTH, WIDTH_STEP = 0.2, 6.0, 0.1

# Wide layout, but the content stays at a readable width on big screens.
# Below 640 px Streamlit stacks the columns: settings first, then the map.
PAGE_CSS = """
<style>
.block-container { max-width: 1180px; padding-top: 2.5rem; padding-bottom: 3rem; }
@media (max-width: 640px) {
  .block-container { padding: 1.5rem 1rem 2rem; }
  h1 { font-size: 1.8rem !important; }
  /* inside a layer card, keep the colour swatch next to its checkboxes */
  [class*="st-key-card_"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap; gap: 1rem; }
  [class*="st-key-card_"] [data-testid="stColumn"] { width: auto !important; min-width: 0 !important; flex: 1 1 auto !important; }
  [class*="st-key-card_"] [data-testid="stColumn"]:first-child { flex: 0 0 auto !important; }
}
</style>
"""


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


@st.cache_data(max_entries=64, show_spinner=False)
def map_png(lat, lng, layers, colors, widths):
    """PNG of the map; cached so moving a slider back, or downloading, costs nothing.
    Arguments are tuples so they can be hashed cheaply."""
    layers_data = get_layers(lat, lng, list(layers))
    return render_png(layers_data, lat, dict(colors), dict(widths))


def layer_group(key, default_color, toggles, language):
    """One card: colour, on/off checkboxes and line width for a group of layers.
    toggles: [(layer, label, on by default)]. Returns (colour, width, {layer: on})."""
    with st.container(border=True, key=f"card_{key}"):
        color_col, toggles_col = st.columns([1, 3], vertical_alignment="center")
        with color_col:
            color = st.color_picker(key, default_color, key=key, label_visibility="collapsed")
        with toggles_col:
            enabled = {layer: st.checkbox(label, value=on, key=f"on_{layer}") for layer, label, on in toggles}
        width = st.slider(
            Epaisseur_Dictionnary[language], MIN_WIDTH, MAX_WIDTH, DEFAULT_LINE_WIDTH, WIDTH_STEP,
            key=f"width_{key}", disabled=not any(enabled.values()),
        )
    return color, width, enabled


def run():
    st.set_page_config(page_title="Beautiful Map Designer", page_icon="🗺️", layout="wide")
    st.markdown(PAGE_CSS, unsafe_allow_html=True)

    col_title, col_language = st.columns([3, 1], vertical_alignment="bottom")
    with col_language:
        language = st.selectbox(
            "Language",
            ("French", "English", "Chinese", "Italian", "Spanish", "Breton"),
            label_visibility="collapsed",
        )
    with col_title:
        st.title("Beautiful Map Designer !")

    settings, preview = st.columns([2, 3], gap="large")

    with settings:
        cities = load_cities()
        city_query = st.text_input(Ville_Dictionnary[language], "Angers",
                                   help=f"{Exemple_Dictionnary[language]} : Aix-en-Provence → aixenprovence")
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

        # 2 x 2 grid of cards (one column on phones)
        row1 = st.columns(2)
        row2 = st.columns(2)
        with row1[0]:
            water = layer_group("waterways", "#00ffff",
                                [("waterways", Cours_d_eaux_Dictionnary[language], True)], language)
        with row1[1]:
            coast = layer_group("coastline", "#c0c0c0",
                                [("coastline", Littoral_Dictionnary[language], True)], language)
        with row2[0]:
            roads = layer_group("trunk", "#ffd700", [
                ("trunk", Tronçons_Dictionnary[language], True),
                ("motorway", Autoroutes_Dictionnary[language], False),
                ("primary", Boulevards_Dictionnary[language], False),
            ], language)
        with row2[1]:
            trees = layer_group("tree", "#00a67d",
                                [("tree", Haies_Dictionnary[language], False)], language)

    colors, widths, layers = {}, {}, []
    for color, width, enabled in (water, coast, roads, trees):
        for layer, on in enabled.items():
            colors[layer], widths[layer] = color, width
            if on:
                layers.append(layer)

    with preview:
        try:
            with st.spinner("OpenStreetMap…"):
                png = map_png(city_lat, city_lng, tuple(layers),
                              tuple(sorted(colors.items())), tuple(sorted(widths.items())))
        except MapDataError as exc:
            st.error(str(exc))
            st.stop()

        st.image(png, width="stretch")
        st.download_button(
            label="Download PNG",
            data=png,
            file_name=f"{normalize(city['city_ascii'])}_map.png",
            mime="image/png",
            on_click="ignore",
            type="primary",
            width="stretch",
        )
        st.link_button(
            "Je ne vends pas les cartes, si vous voulez soutenir mon travail vous pouvez me faire un don",
            "https://liberapay.com/SchwarzLowe",
            width="stretch",
        )


if __name__ == "__main__":
    run()
