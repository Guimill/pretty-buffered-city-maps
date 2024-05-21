import streamlit_folium as stf
import requests

def create_map(city_lat, city_lng, radius=500):
    m = stf.folium.Map(location=[city_lat, city_lng], zoom_start=10, no_touch=True, zoom_control=False, dragging=False, scrollWheelZoom=False)

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
    
    return m

def add_elements_to_map(data, m, colors, options):
    for element in data['elements']:
        if 'geometry' in element:
            coordinates = [(node['lat'], node['lon']) for node in element['geometry']]
            highway_type = element['tags'].get('highway')
            natural_type = element['tags'].get('natural')
            waterway_type = element['tags'].get('waterway')

            if options['waterways_on'] and waterway_type == 'river':
                stf.folium.PolyLine(locations=coordinates, color=colors['waterways']).add_to(m)
            elif options['trunk_on'] and highway_type == 'trunk':
                stf.folium.PolyLine(locations=coordinates, color=colors['trunk']).add_to(m)
            elif options['motorway_on'] and highway_type == 'motorway':
                stf.folium.PolyLine(locations=coordinates, color=colors['trunk']).add_to(m)
            elif options['primary_on'] and highway_type == 'primary':
                stf.folium.PolyLine(locations=coordinates, color=colors['trunk']).add_to(m)
            elif options['coastline_on'] and natural_type == 'coastline':
                stf.folium.PolyLine(locations=coordinates, color=colors['coastline']).add_to(m)
            elif options['tree_on'] and natural_type == 'tree_row':
                stf.folium.PolyLine(locations=coordinates, color=colors['tree']).add_to(m)
    
    return m

def fetch_map_data(city_lat, city_lng):
    overpass_url = "http://overpass-api.de/api/interpreter"
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
    return data
