import streamlit as st
import utils
import datetime
import pandas as pd
import random
import pydeck as pdk

random.seed(0)

today = datetime.datetime.now() + datetime.timedelta(days=1)

# TODO
# Photos villes
# Météo
# Mettre sous forme de cart
# Lien vers SNCF Connect
# Prix sans MAX
# Correspondances
# Flexibilité
# Background picture
# chatbot

tab1, tab2 = st.tabs(["Trouver une destination", "Connections"])

with tab1:
    st.title("TGV Max Trip Finder")
    all_towns = utils.get_all_towns()
    station = st.selectbox("Entre ta station de départ :", all_towns, index=all_towns.index("PARIS (intramuros)"), key=random.randint(0, int(1e6)))
    dates = st.date_input(
        "Entre tes dates :",
        [today, today],
        min_value=today,
        max_value=today + datetime.timedelta(days=30),
        help='Rentre deux fois la même date pour un aller retour dans la journée!',
        format="DD/MM/YYYY",
    )
    # preferences = st.multiselect("Select your preferences:", ["Fastest", "Cheapest", "Shortest route"])

    if st.button("Trouver mon voyage idéal ", key=random.randint(0, int(1e6))):
        # Run your trip query function here
        print(station, dates)
        df = utils.find_optimal_trips(station, dates)
        print(df)
        df = df[df["temps_sur_place"] > 0]
        df['temps_aller'] = pd.to_datetime(df['heure_arrivee'], format='%H:%M') - pd.to_datetime(df['heure_depart'],
                                                                                                 format='%H:%M')

        # df['heure_arrivee'] = pd.to_datetime(df['heure_arrivee'], format='%H:%M')
        # Iterate over each unique destination
        # Iterate over each unique destination
        for destination in df['destination'].unique():
            # Filter trips for the current destination
            destination_trips = df[df['destination'] == destination]

            # Calculate the minimum trip duration (earliest departure to arrival)
            min_trip_duration = destination_trips['temps_aller'].min()

            # Calculate the maximum time spent at the destination
            max_time_at_destination = destination_trips['temps_sur_place'].max()

            # Create a stylish expander for the destination
            expander_text = f"**🚄 {destination}** ⏱️ **Durée de l'aller:** {utils.format_duration(min_trip_duration)} 🎉 **Temps sur place:** {max_time_at_destination} heures"
            with st.expander(expander_text):
                st.write(f"### Voyages possibles pour {destination}:")

                # Display all trips for the destination
                for _, trip in destination_trips.iterrows():
                    st.write(
                        f"- **Aller**: {trip['heure_depart']} - {trip['heure_arrivee']}, **Retour**: {trip['retour_heure_depart']} - {trip['retour_heure_arrivee']}")

with tab2:
    st.title("TGV Max Trip Finder: Connexions")
    all_towns = utils.get_all_towns()
    station_depart = st.multiselect("Entre ta station de départ :", all_towns, key=random.randint(0, int(1e6)))
    station_arrivee = st.multiselect("Entre ta station d'arrivée :", all_towns, key=random.randint(0, int(1e6)))
    dates = st.date_input(
        "Entre la date :",
        [today, today],
        min_value=today,
        max_value=today + datetime.timedelta(days=30),
        format="DD/MM/YYYY",
    )

    nombre_max_connections = st.select_slider("Nombre maximal de connexions",
        options=range(6),
    )

    if st.button("Trouver mon voyage idéal ", key=random.randint(0, int(1e6))):
        # print(dates, station_depart, station_arrivee)
        results = utils.get_trip_connections(dates, station_depart, station_arrivee)
        for result in results:
            expander_text = (f"**🚄 {result["train_list"][0][0]} -> {result["train_list"][-1][2]}** ⏱️ \
                              **Durée totale:** {utils.format_duration(result["duration"])} \
                                {result["train_list"][0][1]} -> {result["train_list"][-1][3]}")
            # expander_text = result["route_name"]
            with st.expander(expander_text):
                for train in result["train_list"]:
                    container = st.container(border=True)
                    container.write(f"Train n°{train[4]}")
                    container.write(f"    Départ de {train[0]} à {train[1]}")
                    container.write(f"    Arrivée à {train[2]} à {train[3]}")
