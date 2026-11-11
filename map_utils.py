"""OpenStreetMap download, caching and rendering for the circular city maps.

Speed strategy:
- only the layers that are switched on are downloaded,
- several missing layers are fetched in a single Overpass request,
- only the visible disc is requested (bbox + server-side clipping),
- lines are clipped to the disc and simplified with shapely,
- each layer is cached on disk, so a city is downloaded only once.
"""
import gzip
import io
import json
import math
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

import folium
import matplotlib

matplotlib.use("Agg")  # headless backend, no display needed
import matplotlib.pyplot as plt
import requests
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle
from shapely.geometry import LineString, Point

BACKGROUND_COLOR = "#0e1117"
RING_COLOR = "white"

# Folium map settings. CircleMarker radii are in screen pixels, so the visible
# area depends on the zoom level.
ZOOM = 10
OUTER_RADIUS_PX = 500
INNER_RADIUS_PX = OUTER_RADIUS_PX - 250
MAP_WIDTH, MAP_HEIGHT = 700, 600

# Lines are simplified with this tolerance (metres): ~1/6 of a screen pixel at
# zoom 10, invisible on the map and on the PNG, but it removes most points.
SIMPLIFY_TOLERANCE_M = 25

# Layer name -> (Overpass filter, predicate on the way's tags)
LAYERS = {
    "waterways": ('way["waterway"="river"]', lambda t: t.get("waterway") == "river"),
    "coastline": ('way["natural"="coastline"]', lambda t: t.get("natural") == "coastline"),
    "trunk": ('way["highway"="trunk"]', lambda t: t.get("highway") == "trunk"),
    "motorway": ('way["highway"="motorway"]', lambda t: t.get("highway") == "motorway"),
    "primary": ('way["highway"="primary"]', lambda t: t.get("highway") == "primary"),
    "tree": ('way["natural"="tree_row"]', lambda t: t.get("natural") == "tree_row"),
}

# Overpass rejects requests sent with the default "python-requests" User-Agent
# (HTTP 406), so we identify the app explicitly and try several mirrors.
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
HEADERS = {"User-Agent": "pretty-buffered-city-maps/2.1 (Streamlit app)"}

CACHE_DIR = Path(__file__).parent / ".cache" / "osm"
CACHE_VERSION = 1  # bump when the stored format or the query area changes


class MapDataError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# Geometry helpers: a simple local projection in metres centred on the city.
# Accurate enough at this scale (~30 km) and much faster than pyproj.
# --------------------------------------------------------------------------- #
def meters_per_pixel(lat, zoom=ZOOM):
    """Web Mercator ground resolution at a given latitude and zoom."""
    return 156543.03392 * math.cos(math.radians(lat)) / (2 ** zoom)


def disc_radius_m(lat):
    return INNER_RADIUS_PX * meters_per_pixel(lat)


def _scales(lat):
    m_per_deg_lat = 111_320.0
    m_per_deg_lng = 111_320.0 * math.cos(math.radians(lat))
    return m_per_deg_lat, m_per_deg_lng


def _bbox(lat, lng):
    r = disc_radius_m(lat) * 1.02
    k_lat, k_lng = _scales(lat)
    return (lat - r / k_lat, lng - r / k_lng, lat + r / k_lat, lng + r / k_lng)


def _lines_to_latlng(lines, lat, lng):
    k_lat, k_lng = _scales(lat)
    return [[(lat + y / k_lat, lng + x / k_lng) for x, y in line] for line in lines]


def _clip_and_simplify(geometry, lat, lng, disc):
    """OSM node list -> list of simplified lines (int metres) inside the disc."""
    k_lat, k_lng = _scales(lat)
    pts = [((n["lon"] - lng) * k_lng, (n["lat"] - lat) * k_lat) for n in geometry if n]
    if len(pts) < 2:
        return []
    clipped = LineString(pts).intersection(disc)
    if clipped.is_empty:
        return []
    clipped = clipped.simplify(SIMPLIFY_TOLERANCE_M, preserve_topology=False)
    parts = getattr(clipped, "geoms", [clipped])
    out = []
    for part in parts:
        if part.geom_type == "LineString" and len(part.coords) >= 2:
            out.append([(round(x), round(y)) for x, y in part.coords])
    return out


# --------------------------------------------------------------------------- #
# Disk cache
# --------------------------------------------------------------------------- #
def _cache_path(layer, lat, lng):
    return CACHE_DIR / f"v{CACHE_VERSION}_{layer}_{lat:.4f}_{lng:.4f}.json.gz"


def _cache_get(layer, lat, lng):
    path = _cache_path(layer, lat, lng)
    try:
        with gzip.open(path, "rt") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _cache_put(layer, lat, lng, lines):
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _cache_path(layer, lat, lng).with_suffix(".tmp")
        with gzip.open(tmp, "wt") as f:
            json.dump(lines, f, separators=(",", ":"))
        tmp.replace(_cache_path(layer, lat, lng))
    except OSError:
        pass  # read-only disk: the app still works, just without cache


# --------------------------------------------------------------------------- #
# Overpass
# --------------------------------------------------------------------------- #
HEDGE_DELAY_S = 12  # wait this long for a mirror before also asking the next one
REQUEST_TIMEOUT_S = 150


def _post(url, query):
    response = requests.post(url, data={"data": query}, headers=HEADERS, timeout=REQUEST_TIMEOUT_S)
    response.raise_for_status()
    data = response.json()
    # Overpass reports server-side timeouts/out-of-memory inside a 200 response
    if "remark" in data and not data.get("elements"):
        raise ValueError(data["remark"])
    return data


def _overpass(query):
    """Hedged request: start with the first mirror, add the next one every
    HEDGE_DELAY_S seconds (or as soon as one fails), return the first success."""
    errors = []
    pool = ThreadPoolExecutor(max_workers=len(OVERPASS_URLS))
    pending = {}
    urls = iter(OVERPASS_URLS)
    try:
        while True:
            url = next(urls, None)
            if url is not None:
                pending[pool.submit(_post, url, query)] = url
            if not pending:
                break
            done, _ = wait(pending, timeout=HEDGE_DELAY_S if url else None, return_when=FIRST_COMPLETED)
            for future in done:
                failed_url = pending.pop(future)
                try:
                    return future.result()
                except (requests.RequestException, ValueError) as exc:
                    errors.append(f"{failed_url}: {exc}")
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    raise MapDataError("Overpass API unavailable:\n" + "\n".join(errors))


def get_layers(lat, lng, layers):
    """Return {layer: [lines in local metres]} for the requested layers.

    Cached layers are read from disk; all missing ones are downloaded in one
    Overpass request, clipped to the visible disc and stored.
    """
    result = {}
    missing = []
    for layer in layers:
        cached = _cache_get(layer, lat, lng)
        if cached is None:
            missing.append(layer)
        else:
            result[layer] = cached
    if not missing:
        return result

    bbox = ",".join(f"{v:.5f}" for v in _bbox(lat, lng))
    statements = "".join(f"{LAYERS[layer][0]}({bbox});" for layer in missing)
    # "out tags geom(bbox)" = only tags + coordinates, cut to the bbox by the server
    data = _overpass(f"[out:json][timeout:120];({statements});out tags geom({bbox});")

    disc = Point(0, 0).buffer(disc_radius_m(lat), quad_segs=64)
    fetched = {layer: [] for layer in missing}
    for element in data.get("elements", []):
        tags = element.get("tags", {})
        for layer in missing:
            if LAYERS[layer][1](tags):
                fetched[layer].extend(_clip_and_simplify(element.get("geometry", []), lat, lng, disc))
                break

    for layer, lines in fetched.items():
        _cache_put(layer, lat, lng, lines)
    result.update(fetched)
    return result


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def create_map(city_lat, city_lng, radius=OUTER_RADIUS_PX):
    # No base tiles: the white circle covers the whole map anyway, so loading
    # OSM tiles would only slow the page down.
    m = folium.Map(
        location=[city_lat, city_lng],
        zoom_start=ZOOM,
        tiles=None,
        zoom_control=False,
        dragging=False,
        scrollWheelZoom=False,
        doubleClickZoom=False,
        touchZoom=False,
        keyboard=False,
    )
    folium.CircleMarker(
        location=[city_lat, city_lng], radius=radius, color=RING_COLOR,
        stroke=False, fill=True, fill_opacity=1,
    ).add_to(m)
    folium.CircleMarker(
        location=[city_lat, city_lng], radius=radius - 250, color=BACKGROUND_COLOR,
        stroke=False, fill=True, fill_opacity=1,
    ).add_to(m)
    return m


def add_layers_to_map(m, layers_data, colors, city_lat, city_lng):
    # One multi-polyline per layer instead of one object per OSM way.
    for layer, lines in layers_data.items():
        if lines:
            folium.PolyLine(
                locations=_lines_to_latlng(lines, city_lat, city_lng),
                color=colors[layer],
                weight=2,
            ).add_to(m)
    return m


def render_png(layers_data, city_lat, colors, size_px=1200):
    """Render the circular map as a PNG with matplotlib (no browser needed)."""
    inner_r = disc_radius_m(city_lat)
    outer_r = OUTER_RADIUS_PX * meters_per_pixel(city_lat)
    frame_r = inner_r * 1.12  # white ring around the dark disc

    dpi = 200
    fig = plt.figure(figsize=(size_px / dpi, size_px / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-frame_r, frame_r)
    ax.set_ylim(-frame_r, frame_r)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(RING_COLOR)

    ax.add_patch(Circle((0, 0), outer_r, color=RING_COLOR, zorder=0))
    ax.add_patch(Circle((0, 0), inner_r, color=BACKGROUND_COLOR, zorder=1))

    for layer, lines in layers_data.items():
        if lines:
            ax.add_collection(LineCollection(lines, colors=colors[layer], linewidths=1.2, zorder=2))

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=dpi, facecolor=fig.get_facecolor())
    plt.close(fig)
    return buffer.getvalue()
