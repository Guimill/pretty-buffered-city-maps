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
import time
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless backend, no display needed
import matplotlib.pyplot as plt
import requests
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle
from shapely.geometry import LineString, Point

BACKGROUND_COLOR = "#0e1117"
RING_COLOR = "white"

# The visible area: a disc of 250 px at Web Mercator zoom 10 (~30 km across).
# Changing these changes the area downloaded from OpenStreetMap (bump CACHE_VERSION).
ZOOM = 10
INNER_RADIUS_PX = 250

# Default line width (matplotlib points on the 1200 px image)
DEFAULT_LINE_WIDTH = 1.2

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
# overpass-api.de balances between two backends (z and lz4); when one is down,
# half the requests fail at once, so "z" is also asked directly.
OVERPASS_URLS = [
    "https://z.overpass-api.de/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
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
HEDGE_DELAY_S = 12      # wait this long for a mirror before also asking the next one
REQUEST_TIMEOUT_S = 150
TOTAL_BUDGET_S = 180    # give up after this long
MAX_ATTEMPTS = 3        # per mirror
RETRY_DELAY_S = 4       # x attempt number: overloaded mirrors often answer on the next try


def _post(url, query):
    response = requests.post(url, data={"data": query}, headers=HEADERS, timeout=REQUEST_TIMEOUT_S)
    response.raise_for_status()
    data = response.json()
    # Overpass reports server-side timeouts/out-of-memory inside a 200 response
    if "remark" in data and not data.get("elements"):
        raise ValueError(data["remark"])
    return data


def _retryable(exc):
    """Busy/overloaded answers (429, 5xx, refused connection) are worth another try;
    a request that already ran into the read timeout is not."""
    if isinstance(exc, requests.Timeout):
        return False
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return True


def _overpass(query):
    """Hedged request with retries.

    Start with the first mirror and add the next one every HEDGE_DELAY_S seconds,
    or at once when nothing is running. A mirror that fails with a "busy" error
    is asked again a little later (up to MAX_ATTEMPTS). The first success wins.
    """
    deadline = time.monotonic() + TOTAL_BUDGET_S
    errors = []
    attempts = dict.fromkeys(OVERPASS_URLS, 0)
    ready = deque(OVERPASS_URLS)  # mirrors that can be asked now
    retry_at = {}                 # mirror -> when it can be asked again
    pending = {}                  # future -> mirror
    last_start = float("-inf")
    pool = ThreadPoolExecutor(max_workers=len(OVERPASS_URLS))
    try:
        while time.monotonic() < deadline:
            now = time.monotonic()
            for url, when in list(retry_at.items()):
                if when <= now:
                    ready.append(url)
                    del retry_at[url]
            if ready and (not pending or now - last_start >= HEDGE_DELAY_S):
                url = ready.popleft()
                attempts[url] += 1
                pending[pool.submit(_post, url, query)] = url
                last_start = now
            if not (pending or ready or retry_at):
                break

            wake = [deadline]
            if ready:
                wake.append(last_start + HEDGE_DELAY_S)
            if retry_at:
                wake.append(min(retry_at.values()))
            timeout = max(0.0, min(wake) - time.monotonic())
            if pending:
                done, _ = wait(pending, timeout=timeout, return_when=FIRST_COMPLETED)
            else:
                time.sleep(timeout)
                done = ()
            for future in done:
                url = pending.pop(future)
                try:
                    return future.result()
                except (requests.RequestException, ValueError) as exc:
                    errors.append(f"{url} (try {attempts[url]}): {exc}")
                    if attempts[url] < MAX_ATTEMPTS and _retryable(exc):
                        retry_at[url] = time.monotonic() + RETRY_DELAY_S * attempts[url]
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    if pending:
        errors.append("no answer in time from: " + ", ".join(pending.values()))
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
def render_png(layers_data, city_lat, colors, widths=None, size_px=1200):
    """Render the circular map as a PNG with matplotlib (no browser needed).

    The same image is shown in the page and downloaded, so the preview is exact.
    widths: {layer: line width in points}, missing layers use DEFAULT_LINE_WIDTH.
    """
    widths = widths or {}
    inner_r = disc_radius_m(city_lat)
    frame_r = inner_r * 1.12  # white ring around the dark disc

    dpi = 200
    fig = plt.figure(figsize=(size_px / dpi, size_px / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-frame_r, frame_r)
    ax.set_ylim(-frame_r, frame_r)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(RING_COLOR)

    disc = ax.add_patch(Circle((0, 0), inner_r, color=BACKGROUND_COLOR, zorder=1))

    for layer, lines in layers_data.items():
        if lines:
            collection = ax.add_collection(LineCollection(
                lines, colors=colors[layer], linewidths=widths.get(layer, DEFAULT_LINE_WIDTH),
                capstyle="round", joinstyle="round", zorder=2,
            ))
            collection.set_clip_path(disc)  # thick lines stay inside the disc

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=dpi, facecolor=fig.get_facecolor())
    plt.close(fig)
    return buffer.getvalue()
