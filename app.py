import streamlit as st
import utils
import datetime
import pandas as pd
today = datetime.datetime.now()+datetime.timedelta(days=1)

def format_duration(td):
    total_minutes = int(td.total_seconds() // 60)
    if total_minutes < 60:
        return f"{total_minutes} minutes"
    else:
        hours = total_minutes // 60
        minutes = total_minutes % 60
        heures_string = "heures"
        if hours == 1:
            heures_string = "heure"
        minutes_string = "minutes"
        if minutes == 1:
            minutes_string = "minute"
        if minutes == 0:
            return f"{hours} {heures_string}"
        else:
            return f"{hours} {heures_string} et {minutes} {minutes_string}"

st.title("TGV Max Trip Finder")
all_towns = utils.get_all_towns()
station = st.selectbox("Entre ta station de départ :", all_towns, index=all_towns.index("PARIS (intramuros)"))
dates = st.date_input(
    "Entre tes dates :",
    [today, today],
    min_value=today,
    max_value=today + datetime.timedelta(days=30),
    help='Rentre deux fois la même date pour un aller retour dans la journée!',
    format="DD/MM/YYYY",
)
# preferences = st.multiselect("Select your preferences:", ["Fastest", "Cheapest", "Shortest route"])

if st.button("Trouver mon voyage idéal "):
    # Run your trip query function here
    df = utils.find_optimal_trips(station, dates)
    df = df[df["temps_sur_place"] > 0]
    df['temps_aller'] = pd.to_datetime(df['Heure_arrivee'], format='%H:%M')-pd.to_datetime(df['Heure_depart'], format='%H:%M')

    # df['Heure_arrivee'] = pd.to_datetime(df['Heure_arrivee'], format='%H:%M')
    # Iterate over each unique destination
    # Iterate over each unique destination
    for destination in df['Destination'].unique():
        # Filter trips for the current destination
        destination_trips = df[df['Destination'] == destination]

        # Calculate the minimum trip duration (earliest departure to arrival)
        min_trip_duration = destination_trips['temps_aller'].min()

        # Calculate the maximum time spent at the destination
        max_time_at_destination = destination_trips['temps_sur_place'].max()

        # Create a stylish expander for the destination
        expander_text = f"**🚄 {destination}** ⏱️ **Durée de l'aller:** {format_duration(min_trip_duration)} 🎉 **Temps sur place:** {max_time_at_destination} heures"
        with st.expander(expander_text):
            st.write(f"### Voyages possibles pour {destination}:")

            # Display all trips for the destination
            for _, trip in destination_trips.iterrows():
                st.write(
                    f"- **Aller**: {trip['Heure_depart']} - {trip['Heure_arrivee']}, **Retour**: {trip['retour_heure_depart']} - {trip['retour_heure_arrivee']}")