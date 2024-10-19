import streamlit as st
import pandas as pd
import pydeck as pdk

# Sample data: List of destinations
data = {
    'name': ['Eiffel Tower', 'Statue of Liberty', 'Great Wall of China', 'Sydney Opera House'],
    'latitude': [48.8584, 40.6892, 40.4319, -33.8568],
    'longitude': [2.2945, -74.0445, 116.5704, 151.2153],
    'info': [
        'An iconic symbol of Paris, France.',
        'A colossal neoclassical sculpture on Liberty Island in New York Harbor.',
        'Ancient series of walls and fortifications in northern China.',
        'A multi-venue performing arts centre in Sydney, Australia.'
    ]
}

df = pd.DataFrame(data)

st.title('World Destinations Map')
st.write('Hover over a point to see more information.')

# Define the layer for the map
layer = pdk.Layer(
    'ScatterplotLayer',
    data=df,
    get_position='[longitude, latitude]',
    get_radius=50000,
    get_color=[255, 0, 0],
    pickable=True
)

# Define the tooltip to show on hover
tooltip = {
    "html": "<b>{name}</b><br/>{info}",
    "style": {
        "backgroundColor": "steelblue",
        "color": "white",
        "fontSize": "14px",
        "padding": "10px",
        "borderRadius": "5px"
    }
}

# Set the initial view of the map
view_state = pdk.ViewState(
    latitude=0,
    longitude=0,
    zoom=1.5,
    pitch=0
)

# Render the map
r = pdk.Deck(
    map_style='mapbox://styles/mapbox/light-v9',
    layers=[layer],
    initial_view_state=view_state,
    tooltip=tooltip
)

st.pydeck_chart(r)
