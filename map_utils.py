import io
import math
import time

import folium
import matplotlib

matplotlib.use("Agg")  # headless backend, no display needed
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle
import requests
import streamlit as st

BACKGROUND_COLOR = "#0e1117"
RING_COLOR = "white"

# Folium map settings. The circles are CircleMarkers whose radius is in screen
# pixels, so the visible area depends on the zoom level.
ZOOM = 10
OUTER_RADIUS_PX = 500
INNER_RADIUS_PX = OUTER_RADIUS_PX - 250

# Overpass rejects requests sent with the default "python-requests" User-Agent
# (HTTP 406), so we identify the app explicitly and try several mirrors.
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
HEADERS = {"User-Agent": "pretty-buffered-city-maps/2.0 (Streamlit app)"}


class MapDataError(RuntimeError):
    pass


def meters_per_pixel(lat, zoom=ZOOM):
    """Web Mercator ground resolution at a given latitude and zoom."""
    return 156543.03392 * math.cos(math.radians(lat)) / (2 ** zoom)


def create_map(city_lat, city_lng, radius=OUTER_RADIUS_PX):
    m = folium.Map(
        location=[city_lat, city_lng],
        zoom_start=ZOOM,
        zoom_control=False,
        dragging=False,
        scrollWheelZoom=False,
        doubleClickZoom=False,
        touchZoom=False,
    )

    folium.CircleMarker(
        location=[city_lat, city_lng],
        radius=radius,
        color=RING_COLOR,
        stroke=False,
        fill=True,
        fill_opacity=1,
    ).add_to(m)

    folium.CircleMarker(
        location=[city_lat, city_lng],
        radius=radius - 250,
        color=BACKGROUND_COLOR,
        stroke=False,
        fill=True,
        fill_opacity=1,
    ).add_to(m)

    return m


def _element_category(element, options):
    """Return the color key for an OSM way, or None if it must not be drawn."""
    tags = element.get("tags", {})
    highway_type = tags.get("highway")
    natural_type = tags.get("natural")
    waterway_type = tags.get("waterway")

    if options["waterways_on"] and waterway_type == "river":
        return "waterways"
    if options["trunk_on"] and highway_type == "trunk":
        return "trunk"
    if options["motorway_on"] and highway_type == "motorway":
        return "trunk"
    if options["primary_on"] and highway_type == "primary":
        return "trunk"
    if options["coastline_on"] and natural_type == "coastline":
        return "coastline"
    if options["tree_on"] and natural_type == "tree_row":
        return "tree"
    return None


def _iter_lines(data, options):
    for element in data.get("elements", []):
        if "geometry" not in element:
            continue
        category = _element_category(element, options)
        if category is None:
            continue
        coordinates = [(node["lat"], node["lon"]) for node in element["geometry"] if node]
        if len(coordinates) >= 2:
            yield category, coordinates


def add_elements_to_map(data, m, colors, options):
    for category, coordinates in _iter_lines(data, options):
        folium.PolyLine(locations=coordinates, color=colors[category]).add_to(m)
    return m


def render_png(data, city_lat, city_lng, colors, options, size_px=1200):
    """Render the circular map as a PNG with matplotlib (no browser needed)."""
    mpp = meters_per_pixel(city_lat)
    inner_r = INNER_RADIUS_PX * mpp
    outer_r = OUTER_RADIUS_PX * mpp
    # Leave a white ring around the dark disc, like on the interactive map.
    frame_r = inner_r * 1.12

    m_per_deg_lat = 111_320.0
    m_per_deg_lng = 111_320.0 * math.cos(math.radians(city_lat))

    def project(lat, lng):
        return ((lng - city_lng) * m_per_deg_lng, (lat - city_lat) * m_per_deg_lat)

    dpi = 200
    fig = plt.figure(figsize=(size_px / dpi, size_px / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-frame_r, frame_r)
    ax.set_ylim(-frame_r, frame_r)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(RING_COLOR)

    ax.add_patch(Circle((0, 0), outer_r, color=RING_COLOR, zorder=0))
    disc = Circle((0, 0), inner_r, color=BACKGROUND_COLOR, zorder=1)
    ax.add_patch(disc)

    segments = {key: [] for key in colors}
    for category, coordinates in _iter_lines(data, options):
        segments[category].append([project(lat, lng) for lat, lng in coordinates])

    for category, lines in segments.items():
        if not lines:
            continue
        collection = LineCollection(lines, colors=colors[category], linewidths=1.2, zorder=2)
        collection.set_clip_path(disc)
        ax.add_collection(collection)

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=dpi, facecolor=fig.get_facecolor())
    plt.close(fig)
    return buffer.getvalue()


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def fetch_map_data(city_lat, city_lng):
    overpass_query = f"""
        [out:json][timeout:120];
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

    errors = []
    for attempt in range(2):
        for url in OVERPASS_URLS:
            try:
                response = requests.post(
                    url, data={"data": overpass_query}, headers=HEADERS, timeout=180
                )
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                errors.append(f"{url}: {exc}")
        time.sleep(2 * (attempt + 1))

    raise MapDataError("Overpass API unavailable:\n" + "\n".join(errors[-len(OVERPASS_URLS):]))
