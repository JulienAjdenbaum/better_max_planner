import pandas as pd
from sqlalchemy import create_engine, text
import requests
from io import StringIO
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import numpy as np
import time
# pd.set_option('display.max_rows', 500)
# pd.set_option('display.max_columns', 500)
# from app import destination

engine = create_engine('sqlite:///tgvmax.db')

def format_duration(td):
    total_minutes = int(td.total_seconds() // 60)
    if total_minutes < 60:
        return f"{total_minutes}m"
    else:
        hours = total_minutes // 60
        minutes = total_minutes % 60
        if minutes == 0:
            return f"{hours}h"
        else:
            return f"{hours}h{minutes}m"

def scheduled_task():
    print("Did task")

def test_app_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_task, 'interval', seconds=1)
    scheduler.start()

def update_db(engine):
    # URL to download the CSV file
    url = "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/tgvmax/exports/csv"
    print("Starting data download")
    # Send the GET request to download the file
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        csv_data = StringIO(response.text)
        print("Data has been received, processing it")
        new_data_df = pd.read_csv(csv_data, sep=";")
        new_data_df.rename(columns={"od_happy_card": "DISPO"}, inplace=True)
        new_data_df["UID"] = new_data_df.index
        new_data_df.to_sql('TGVMAX', con=engine, index=False, if_exists='replace')
        print("Data update done")
    else:
        print(f"Failed to download the file. Status code: {response.status_code}")
        print(response.text)


def run_query(query, params=None, engine=engine, as_list=False):
    with engine.connect() as connection:
        result = connection.execute(text(query), params or {})
        if as_list:
            return [row[0] for row in result.fetchall()]
        return pd.DataFrame(result.fetchall(), columns=result.keys())


def get_all_towns():
    """Return all distinct towns available in the dataset."""
    query = """
        SELECT DISTINCT origine AS Town FROM TGVMAX
        UNION
        SELECT DISTINCT destination AS Town FROM TGVMAX;
    """

    return run_query(query, as_list=True)


def find_optimal_trips(station, dates):
    """Return all distinct towns available in the dataset."""
    # Convert string dates to datetime objects
    date1 = datetime.strptime(dates[0], '%Y-%m-%d')
    date2 = datetime.strptime(dates[1], '%Y-%m-%d')
    n_jours = (date2 - date1).days
    print(n_jours)
    # query = """
    # SELECT distinct aller.destination

    # FROM TGVMAX as aller
    # JOIN (SELECT *
    #       FROM TGVMAX 
    #       WHERE date = :date2 AND destination = :ville AND DISPO = 'OUI' AND Axe != 'IC NUIT') as retour
    # ON aller.destination = retour.origine
    # WHERE aller.date = :date1 AND aller.DISPO = 'OUI' AND aller.origine = :ville 
    # AND aller.Axe != 'IC NUIT'
    # AND aller.heure_arrivee < retour.heure_depart
    # -- AND aller.destination = "RENNES"
    # AND aller.heure_depart > 10
    # ORDER BY (24 - aller.heure_arrivee + retour.heure_depart) DESC
    # """
    
    # Generate placeholders for the IN clause
    date_placeholders = ', '.join([f':date_{i}' for i in range(len(dates))])
    
    query = f"""
    SELECT *
    FROM TGVMAX as aller
    WHERE aller.date in ({date_placeholders}) AND aller.origine = :ville AND axe = "SUD EST" AND aller.destination = "VALENCE TGV" AND DISPO = "OUI";
    """
    
    # Build parameters dictionary
    params = {}
    for i, date in enumerate(dates):
        params[f'date_{i}'] = date
    params['ville'] = station

    return run_query(query, params=params, as_list=False)


def find_optimal_destinations(station, dates):
    """Find optimal destinations for round trips from a given station on specified dates."""
    # Handle both single date and date pair inputs
    if isinstance(dates, str):
        # Single date provided - use same date for outbound and return
        date1 = datetime.strptime(dates, '%Y-%m-%d')
        date2 = date1
        print(f"Planning day trip on {dates}")
    else:
        # Date pair provided
        date1 = datetime.strptime(dates[0], '%Y-%m-%d')
        date2 = datetime.strptime(dates[1], '%Y-%m-%d')
        n_jours = (date2 - date1).days
        print(f"Planning trip for {n_jours} days")
    
    query = """
    SELECT 
        aller.destination,
        aller.heure_depart as outbound_departure,
        aller.heure_arrivee as outbound_arrival,
        retour.heure_depart as return_departure,
        retour.heure_arrivee as return_arrival,
        aller.train_no as outbound_train,
        retour.train_no as return_train,
        aller.axe as outbound_axe,
        retour.axe as return_axe
    FROM TGVMAX as aller
    JOIN (SELECT *
          FROM TGVMAX 
          WHERE date = :date2 AND destination = :ville AND DISPO = 'OUI' AND Axe != 'IC NUIT') as retour
    ON aller.destination = retour.origine
    WHERE aller.date = :date1 AND aller.DISPO = 'OUI' AND aller.origine = :ville 
    AND aller.Axe != 'IC NUIT'
    AND aller.heure_arrivee < retour.heure_depart
    AND aller.heure_depart > 10
    ORDER BY (24 - aller.heure_arrivee + retour.heure_depart) DESC
    """
    
    # Build parameters dictionary
    params = {
        'date1': date1.strftime('%Y-%m-%d'),
        'date2': date2.strftime('%Y-%m-%d'),
        'ville': station
    }

    result = run_query(query, params=params, as_list=False)
    
    # Calculate travel times and time at destination
    trips_data = []
    for _, row in result.iterrows():
        # Parse times
        outbound_depart = datetime.strptime(row['outbound_departure'], '%H:%M')
        outbound_arrive = datetime.strptime(row['outbound_arrival'], '%H:%M')
        return_depart = datetime.strptime(row['return_departure'], '%H:%M')
        return_arrive = datetime.strptime(row['return_arrival'], '%H:%M')
        
        # Handle overnight trips (arrival time earlier than departure time)
        if outbound_arrive < outbound_depart:
            outbound_arrive += timedelta(days=1)
        if return_arrive < return_depart:
            return_arrive += timedelta(days=1)
        
        # Handle cases where return departure is before outbound arrival
        if return_depart < outbound_arrive:
            return_depart += timedelta(days=1)
            return_arrive += timedelta(days=1)
        
        # Exclude trips where outbound arrival is on the next day (not a valid day trip)
        if (outbound_arrive - outbound_depart) >= timedelta(days=1):
            continue
        # Exclude trips where return departure is not on the same day as outbound departure
        if return_depart.date() != outbound_depart.date():
            continue
        
        # Calculate travel times
        outbound_travel_time = outbound_arrive - outbound_depart
        return_travel_time = return_arrive - return_depart
        total_travel_time = outbound_travel_time + return_travel_time
        
        # Calculate time at destination
        time_at_destination = return_depart - outbound_arrive
        
        trips_data.append({
            'destination': row['destination'],
            'outbound_departure': row['outbound_departure'],
            'outbound_arrival': row['outbound_arrival'],
            'return_departure': row['return_departure'],
            'return_arrival': row['return_arrival'],
            'outbound_train': row['outbound_train'],
            'return_train': row['return_train'],
            'outbound_axe': row['outbound_axe'],
            'return_axe': row['return_axe'],
            'outbound_travel_time': format_duration(outbound_travel_time),
            'return_travel_time': format_duration(return_travel_time),
            'total_travel_time': format_duration(total_travel_time),
            'time_at_destination': format_duration(time_at_destination),
            'time_at_destination_minutes': time_at_destination.total_seconds() / 60
        })
    
    # Sort by time at destination (descending)
    trips_data.sort(key=lambda x: x['time_at_destination_minutes'], reverse=True)
    
    return trips_data



def preview_query(query, params):
    # This function is only for debugging and should not be used in production
    formatted_query = query
    for key, value in params.items():
        placeholder = f":{key}"
        if isinstance(value, str):
            value = f"'{value}'"
        else:
            value = str(value)
        formatted_query = formatted_query.replace(placeholder, value)
    print(formatted_query)


def get_trip_connections(dates, origins, destinations):
    # print(type(origins))
    # Generate dynamic placeholders for dates
    date_placeholders = ', '.join([f':date_{i}' for i in range(len(dates))])

    # Determine if we should use '=' or 'IN' for origins and destinations
    use_equal_for_origin = len(origins) == 1
    use_equal_for_destination = len(destinations) == 1

    # Generate origin condition
    if use_equal_for_origin:
        origin_condition = f"origine = :origin_0"
    else:
        origin_placeholders = ', '.join([f':origin_{i}' for i in range(len(origins))])
        origin_condition = f"origine IN ({origin_placeholders})"

    # Generate destination condition
    if use_equal_for_destination:
        destination_condition = f"destination = :destination_0"
    else:
        destination_placeholders = ', '.join([f':destination_{i}' for i in range(len(destinations))])
        destination_condition = f"destination IN ({destination_placeholders})"

    query = f"""
        WITH RECURSIVE possible_routes AS (
            -- Base case: Direct trips
            SELECT
                origine,
                destination,
                heure_depart,
                heure_arrivee,
                date,
                0 AS connection_count,
                heure_depart AS first_leg_departure,
                heure_arrivee AS last_leg_arrival,
                CAST(origine || ' -> ' || destination AS TEXT) AS route_description,
                CAST(uid AS TEXT) AS route_uid
            FROM TGVMAX
            WHERE {origin_condition}
              AND date IN ({date_placeholders})
              AND DISPO = 'OUI'
              AND NOT axe = 'IC NUIT'

            UNION ALL

            -- Recursive case: Trips with connections, limit recursion to max_connections
            SELECT
                t.origine,
                t.destination,
                t.heure_depart,
                t.heure_arrivee,
                t.date,
                pr.connection_count + 1 AS connection_count,
                pr.first_leg_departure,
                t.heure_arrivee AS last_leg_arrival,
                CAST(pr.route_description || ' -> ' || t.origine || ' -> ' || t.destination AS TEXT)
                    AS route_description,
                CAST(pr.route_uid || '-' || t.uid AS TEXT) AS route_uid
            FROM TGVMAX t
            JOIN possible_routes pr
              ON t.origine = pr.destination
              AND t.heure_depart > pr.last_leg_arrival
              AND t.date = pr.date
              AND t.DISPO = 'OUI'
              AND NOT t.axe = 'IC NUIT'
            WHERE pr.connection_count < :max_connections
        )
        -- Select only trips that end at the desired destination
        SELECT
            origine,
            destination,
            first_leg_departure,
            last_leg_arrival,
            route_description,
            connection_count,
            date, 
            route_uid
        FROM possible_routes
        WHERE {destination_condition}
        ORDER BY connection_count, first_leg_departure, last_leg_arrival;
    """

    # Build the parameters dictionary
    params = {'max_connections': 0}

    # Add origins to params
    for i, origin in enumerate(origins):
        params[f'origin_{i}'] = origin

    # Add destinations to params
    for i, destination in enumerate(destinations):
        params[f'destination_{i}'] = destination

    # Add dates to params
    for i, date in enumerate(dates):
        params[f'date_{i}'] = date

    # Preview the query (optional)
    preview_query(query, params)

    # Run the query
    result = run_query(query, params=params)
    print(len(result))

    # Increase max_connections until results are found or limit is reached
    while len(result) == 0 and params['max_connections'] < 5:
        print(params['max_connections'])
        params['max_connections'] += 1
        print(f"Increasing max connections to {params['max_connections']}")
        result = run_query(query, params=params)

    result_list = []
    for index, route in result.iterrows():
        trains = list(map(int, route['route_uid'].split('-')))
        query = """
        SELECT origine, heure_depart, destination, heure_arrivee, train_no
        FROM TGVMAX
        WHERE uid=:uid
        """

        train_dic = {}
        train_dic['train_list'] = []
        for index_train, train in enumerate(trains):
            params = {"uid": train}
            train_dic['train_list'].append(list(run_query(query, params=params).values[0]))
        train_dic['route_name'] = route['route_description']
        # print(route.keys)
        train_dic['duration'] = datetime.strptime(route['last_leg_arrival'], '%H:%M') - datetime.strptime(route['first_leg_departure'], '%H:%M')
        result_list.append(train_dic)

    idx = np.argsort([result["duration"] for result in result_list])
    result_list = [result_list[i] for i in idx]
    return result_list





if __name__ == "__main__":
    # update_db(engine)
    # test_app_scheduler()
    # time.sleep(100)
    # Example lists of possible dates, origins, and destinations
    # dates = ["2024-11-10"]
    # # Example lists of possible dates, origins, and destinations
    # # dates = ["2024-10-31", "2024-11-14", "2024-11-15"]
    # IDF = ["PARIS (intramuros)", "AEROPORT CDG2 TGV ROISSY", "MANTES LA JOLIE", "MARNE LA VALLEE CHESSY", "MASSY TGV",
    #        "MASSY PALAISEAU", "VERSAILLES CHANTIERS"]
    # destinations = ["AVIGNON TGV", "AVIGNON CENTRE", "ORANGE", "MONTELIMAR GARE SNCF", "VALENCE TGV RHONE-ALPES SUD",
    #                 "VALENCE VILLE"]
    #
    dates = ("2025-07-13")
    origins = ['PARIS (intramuros)']
    destinations = ['AVIGNON TGV']
    # print(find_optimal_trips(origins[0], dates))
    trips = find_optimal_destinations(origins[0], dates)
    
    if trips:
        print(f"\n{'='*100}")
        print(f"OPTIMAL DESTINATIONS FROM {origins[0].upper()} ON {dates}")
        print(f"{'='*100}")
        
        # Create table header with better spacing
        print(f"{'Destination':<25} {'Outbound':<20} {'Return':<20} {'Total Travel':<15} {'Time at Dest':<15}")
        print(f"{'':<25} {'Depart-Arrive':<20} {'Depart-Arrive':<20} {'Time':<15} {'(hrs:min)':<15}")
        print("-" * 100)
        
        for trip in trips:
            # Handle long destination names by truncating with ellipsis
            dest_name = trip['destination']
            if len(dest_name) > 24:
                dest_name = dest_name[:21] + "..."
            
            print(f"{dest_name:<25} "
                  f"{trip['outbound_departure']}-{trip['outbound_arrival']:<20} "
                  f"{trip['return_departure']}-{trip['return_arrival']:<20} "
                  f"{trip['total_travel_time']:<15} "
                  f"{trip['time_at_destination']:<15}")
        
        print(f"{'='*100}")
        print(f"Found {len(trips)} optimal destinations")
    else:
        print("No optimal destinations found for the given criteria.")
    
    # print(get_trip_connections(dates, origins, destinations))
