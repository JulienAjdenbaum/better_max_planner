import pandas as pd
from sqlalchemy import create_engine, text
import requests
from io import StringIO
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import numpy as np
import time
import os
import json
# pd.set_option('display.max_rows', 500)
# pd.set_option('display.max_columns', 500)
# from app import destination

engine = create_engine('sqlite:///data/tgvmax.db')
logger = logging.getLogger(__name__)

def format_duration(td):
    total_minutes = int(td.total_seconds() // 60)
    
    # Handle negative durations (should not happen in normal cases)
    if total_minutes < 0:
        return "0m"  # Return 0 minutes for invalid durations
    
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
    logger.info("Tâche effectuée")

def remove_past_trips(engine=None):
    """
    Remove all trips from TGVMAX table that have already departed (before now).
    Uses single optimized query for better performance.
    Logs the number of rows removed and the time taken.
    """
    if engine is None:
        from src.utils import engine as default_engine
        engine = default_engine
        
    start_time = time.perf_counter()
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    current_time_str = now.strftime('%H:%M')

    try:
        with engine.begin() as conn:
            # Count rows before deletion
            result = conn.execute(text("SELECT COUNT(*) FROM TGVMAX"))
            before_count = result.fetchone()[0]

            # Single optimized deletion query
            delete_query = text("""
                DELETE FROM TGVMAX 
                WHERE DATE < :today 
                   OR (DATE = :today AND heure_depart < :current_time)
            """)
            conn.execute(delete_query, {"today": today_str, "current_time": current_time_str})

            # Count rows after deletion
            result = conn.execute(text("SELECT COUNT(*) FROM TGVMAX"))
            after_count = result.fetchone()[0]

            removed = before_count - after_count
            elapsed = time.perf_counter() - start_time
            
            logger.info(f"🧹 Removed {removed} past trips from database. Before: {before_count:,}, After: {after_count:,}, Elapsed: {elapsed:.3f}s")
            return {"removed": removed, "before": before_count, "after": after_count, "elapsed": elapsed}
            
    except Exception as e:
        elapsed = time.perf_counter() - start_time
        logger.error(f"❌ Error removing past trips: {e}, Elapsed: {elapsed:.3f}s")
        raise

def test_app_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_task, 'interval', seconds=1)
    scheduler.start()

def update_db(engine):
    """
    Complete database update pipeline:
    1. Download fresh data from SNCF
    2. Replace existing data
    3. Remove past trips
    4. Optimize database (fix inconsistencies and cleanup)
    """
    overall_start = time.perf_counter()
    
    # URL to download the CSV file
    url = "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/tgvmax/exports/csv"
    logger.info("🚀 Starting complete database update pipeline")
    logger.info("📥 Downloading fresh data from SNCF...")
    
    # Send the GET request to download the file
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        csv_data = StringIO(response.text)
        logger.info("📊 Data received, processing...")
        new_data_df = pd.read_csv(csv_data, sep=";")
        new_data_df.rename(columns={"od_happy_card": "DISPO"}, inplace=True)
        new_data_df["UID"] = new_data_df.index
        
        # Get initial row count
        initial_rows = len(new_data_df)
        logger.info(f"📋 Downloaded {initial_rows:,} trip records")
        
        # Replace database
        new_data_df.to_sql('TGVMAX', con=engine, index=False, if_exists='replace')
        logger.info("✅ Database replacement completed")
        
        # Remove past trips
        logger.info("🧹 Removing past trips...")
        past_trips_result = remove_past_trips(engine)
        
        # Optimize database (fix inconsistencies)
        logger.info("🔧 Starting database optimization...")
        optimization_result = optimize_database_complete(engine)
        
        # Final summary
        overall_elapsed = time.perf_counter() - overall_start
        
        logger.info(f"🎉 Complete database update finished successfully!")
        logger.info(f"📊 Summary: {optimization_result['final_available']:,} available trips "
                   f"({optimization_result['final_availability_rate']:.1f}% availability), "
                   f"total time: {overall_elapsed:.3f}s")
        
        return {
            'downloaded_rows': initial_rows,
            'past_trips_removed': past_trips_result.get('removed', 0),
            'optimization_result': optimization_result,
            'total_time': overall_elapsed,
            'success': True
        }
        
    else:
        logger.error(
            "❌ Failed to download data. Status code: %s", response.status_code
        )
        logger.error("Response: %s", response.text)
        return {
            'success': False,
            'error': f"HTTP {response.status_code}",
            'response': response.text
        }


def fix_coupure_non_autorisee(engine=None):
    """
    Fix coupure non autorisée by changing DISPO from 'NON' to 'OUI' 
    for A->B trips where A->C is available and B is intermediate.
    Production version for main database.
    """
    if engine is None:
        from src.utils import engine as default_engine
        engine = default_engine
        
    start_time = time.perf_counter()
    
    # Query to find coupure non autorisée cases
    find_query = text("""
    WITH unavailable_short AS (
        SELECT date, train_no, origine as A, destination as B, 
               heure_depart, heure_arrivee, axe, UID
        FROM TGVMAX 
        WHERE DISPO = 'NON'
    ),
    available_long AS (
        SELECT date, train_no, origine as A, destination as C, 
               heure_depart, heure_arrivee, axe
        FROM TGVMAX 
        WHERE DISPO = 'OUI'
    ),
    intermediate_stations AS (
        SELECT DISTINCT date, train_no, origine, destination, 
               heure_depart, heure_arrivee, axe
        FROM TGVMAX
    )
    SELECT DISTINCT us.UID as short_uid
    FROM unavailable_short us
    JOIN available_long al ON (
        us.date = al.date 
        AND us.train_no = al.train_no
        AND us.A = al.A
        AND us.B != al.C
    )
    JOIN intermediate_stations inter ON (
        us.date = inter.date
        AND us.train_no = inter.train_no
        AND us.B = inter.destination
        AND inter.origine = us.A
    )
    WHERE us.heure_depart = al.heure_depart
      AND inter.heure_arrivee > us.heure_depart
      AND inter.heure_arrivee < al.heure_arrivee
      AND us.heure_arrivee = inter.heure_arrivee
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(find_query)
            uids_to_fix = [row[0] for row in result.fetchall()]
        
        if not uids_to_fix:
            elapsed = time.perf_counter() - start_time
            logger.info(f"✅ No coupure non autorisée issues found ({elapsed:.3f}s)")
            return {'found': 0, 'fixed': 0, 'elapsed': elapsed}
        
        # Fix all issues in batch
        with engine.begin() as conn:
            uid_list = ','.join(map(str, uids_to_fix))
            batch_update_query = text(f"UPDATE TGVMAX SET DISPO = 'OUI' WHERE UID IN ({uid_list})")
            result = conn.execute(batch_update_query)
            fixed_count = result.rowcount
        
        elapsed = time.perf_counter() - start_time
        logger.info(f"🔧 Fixed {fixed_count} coupure non autorisée issues ({elapsed:.3f}s)")
        
        return {
            'found': len(uids_to_fix),
            'fixed': fixed_count,
            'elapsed': elapsed
        }
        
    except Exception as e:
        elapsed = time.perf_counter() - start_time
        logger.error(f"❌ Error fixing coupure non autorisée: {e} ({elapsed:.3f}s)")
        raise


def fix_soudure_non_autorisee_iterative(engine=None):
    """
    Fix soudure non autorisée iteratively by changing DISPO from 'NON' to 'OUI' 
    for A->C trips where both A->B and B->C segments are available.
    Production version for main database.
    """
    if engine is None:
        from src.utils import engine as default_engine
        engine = default_engine
        
    overall_start_time = time.perf_counter()
    
    find_query = text("""
    WITH unavailable_direct AS (
        SELECT date, train_no, origine as A, destination as C, 
               heure_depart, heure_arrivee, axe, UID
        FROM TGVMAX 
        WHERE DISPO = 'NON'
    ),
    available_segments AS (
        SELECT date, train_no, origine, destination, 
               heure_depart, heure_arrivee, axe
        FROM TGVMAX 
        WHERE DISPO = 'OUI'
    )
    SELECT DISTINCT ud.UID as direct_uid
    FROM unavailable_direct ud
    JOIN available_segments seg1 ON (
        ud.date = seg1.date 
        AND ud.train_no = seg1.train_no
        AND ud.A = seg1.origine
        AND seg1.destination != ud.C
    )
    JOIN available_segments seg2 ON (
        ud.date = seg2.date
        AND ud.train_no = seg2.train_no  
        AND seg1.destination = seg2.origine
        AND seg2.destination = ud.C
    )
    WHERE seg1.heure_arrivee <= seg2.heure_depart
    """)
    
    total_fixed = 0
    iteration = 0
    
    try:
        while iteration < 10:  # Safety limit
            iteration += 1
            
            # Find issues in this iteration
            with engine.connect() as conn:
                result = conn.execute(find_query)
                uids_to_fix = [row[0] for row in result.fetchall()]
            
            if not uids_to_fix:
                break
            
            # Fix the issues in batch
            with engine.begin() as conn:
                uid_list = ','.join(map(str, uids_to_fix))
                batch_update_query = text(f"UPDATE TGVMAX SET DISPO = 'OUI' WHERE UID IN ({uid_list})")
                result = conn.execute(batch_update_query)
                fixed_count = result.rowcount
                total_fixed += fixed_count
            
            logger.info(f"🔧 Iteration {iteration}: Fixed {fixed_count} soudure non autorisée issues")
        
        overall_elapsed = time.perf_counter() - overall_start_time
        
        if total_fixed > 0:
            logger.info(f"✅ Completed soudure fixes: {total_fixed} total issues fixed in {iteration} iterations ({overall_elapsed:.3f}s)")
        else:
            logger.info(f"✅ No soudure non autorisée issues found ({overall_elapsed:.3f}s)")
        
        return {
            'total_iterations': iteration,
            'total_fixed': total_fixed,
            'elapsed': overall_elapsed
        }
        
    except Exception as e:
        elapsed = time.perf_counter() - overall_start_time
        logger.error(f"❌ Error fixing soudure non autorisée: {e} ({elapsed:.3f}s)")
        raise


def cleanup_unavailable_trips(engine=None):
    """
    Remove all trips with DISPO='NON' from the database.
    Production version for main database.
    """
    if engine is None:
        from src.utils import engine as default_engine
        engine = default_engine
        
    start_time = time.perf_counter()
    
    try:
        with engine.connect() as conn:
            # Count before cleanup
            result = conn.execute(text("SELECT COUNT(*) FROM TGVMAX"))
            total_before = result.fetchone()[0]
            
            result = conn.execute(text("SELECT COUNT(*) FROM TGVMAX WHERE DISPO = 'NON'"))
            unavailable_count = result.fetchone()[0]
        
        if unavailable_count == 0:
            elapsed = time.perf_counter() - start_time
            logger.info(f"✅ Database cleanup: No unavailable trips to remove ({elapsed:.3f}s)")
            return {'total_before': total_before, 'deleted': 0, 'total_after': total_before, 'elapsed': elapsed}
        
        # Perform cleanup
        with engine.begin() as conn:
            delete_query = text("DELETE FROM TGVMAX WHERE DISPO = 'NON'")
            result = conn.execute(delete_query)
            deleted_count = result.rowcount
            
            result = conn.execute(text("SELECT COUNT(*) FROM TGVMAX"))
            total_after = result.fetchone()[0]
        
        elapsed = time.perf_counter() - start_time
        reduction_percent = ((total_before - total_after) / total_before * 100) if total_before > 0 else 0
        
        logger.info(f"🧹 Database cleanup completed: Deleted {deleted_count:,} unavailable trips, "
                   f"reduced database by {reduction_percent:.1f}% ({elapsed:.3f}s)")
        
        return {
            'total_before': total_before,
            'deleted': deleted_count,
            'total_after': total_after,
            'reduction_percent': reduction_percent,
            'elapsed': elapsed
        }
        
    except Exception as e:
        elapsed = time.perf_counter() - start_time
        logger.error(f"❌ Error during database cleanup: {e} ({elapsed:.3f}s)")
        raise


def optimize_database_complete(engine=None):
    """
    Complete database optimization pipeline:
    1. Fix coupure non autorisée
    2. Fix soudure non autorisée  
    3. Clean up unavailable trips
    Production version for main database with comprehensive logging.
    """
    if engine is None:
        from src.utils import engine as default_engine
        engine = default_engine
        
    overall_start = time.perf_counter()
    
    try:
        # Get initial state
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM TGVMAX"))
            initial_total = result.fetchone()[0]
            
            result = conn.execute(text("SELECT DISPO, COUNT(*) FROM TGVMAX GROUP BY DISPO"))
            initial_stats = dict(result.fetchall())
            
            initial_available = initial_stats.get('OUI', 0)
            initial_unavailable = initial_stats.get('NON', 0)
            initial_rate = (initial_available / initial_total * 100) if initial_total > 0 else 0
        
        logger.info(f"🚀 Starting database optimization: {initial_total:,} trips, "
                   f"{initial_available:,} available ({initial_rate:.1f}%)")
        
        # Step 1: Fix coupure
        coupure_result = fix_coupure_non_autorisee(engine)
        
        # Step 2: Fix soudure
        soudure_result = fix_soudure_non_autorisee_iterative(engine)
        
        # Step 3: Cleanup
        cleanup_result = cleanup_unavailable_trips(engine)
        
        # Get final state
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM TGVMAX"))
            final_total = result.fetchone()[0]
            
            result = conn.execute(text("SELECT DISPO, COUNT(*) FROM TGVMAX GROUP BY DISPO"))
            final_stats = dict(result.fetchall())
            
            final_available = final_stats.get('OUI', 0)
            final_rate = (final_available / final_total * 100) if final_total > 0 else 0
        
        overall_elapsed = time.perf_counter() - overall_start
        
        # Calculate improvements
        new_available = final_available - initial_available
        rate_improvement = final_rate - initial_rate
        
        logger.info(f"🎉 Database optimization completed: +{new_available:,} available trips "
                   f"({rate_improvement:+.1f}% improvement), {final_total:,} total trips, "
                   f"100% available ({overall_elapsed:.3f}s)")
        
        return {
            'initial_available': initial_available,
            'final_available': final_available,
            'new_available_trips': new_available,
            'coupure_fixes': coupure_result['fixed'],
            'soudure_fixes': soudure_result['total_fixed'],
            'trips_deleted': cleanup_result['deleted'],
            'total_time': overall_elapsed,
            'final_availability_rate': final_rate
        }
        
    except Exception as e:
        elapsed = time.perf_counter() - overall_start
        logger.error(f"❌ Database optimization failed: {e} ({elapsed:.3f}s)")
        raise


def run_query(query, params=None, engine=engine, as_list=False):
    logger.debug("Running query: %s params=%s", query.strip(), params)
    with engine.connect() as connection:
        result = connection.execute(text(query), params or {})
        if as_list:
            return [row[0] for row in result.fetchall()]
        return pd.DataFrame(result.fetchall(), columns=result.keys())


def get_all_towns():
    """Return all distinct towns available in the dataset, including station group names."""
    # Get all individual stations from the database
    query = """
        SELECT DISTINCT origine AS Town FROM TGVMAX
        UNION
        SELECT DISTINCT destination AS Town FROM TGVMAX;
    """
    
    individual_stations = run_query(query, as_list=True)
    
    # Add station group names
    group_names = list(STATION_GROUP_MAPPING.keys())
    
    # Combine individual stations and group names
    all_towns = individual_stations + group_names
    
    # Remove duplicates and sort
    all_towns = sorted(list(set(all_towns)))
    
    return all_towns


def find_optimal_trips(station, dates):
    """Return all distinct towns available in the dataset."""
    # Convert string dates to datetime objects
    date1 = datetime.strptime(dates[0], '%Y-%m-%d')
    date2 = datetime.strptime(dates[1], '%Y-%m-%d')
    n_jours = (date2 - date1).days
    logger.debug("Nombre de jours : %s", n_jours)
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
        logger.info("Planification d'un voyage à la journée le %s", dates)
    else:
        # Date pair provided
        date1 = datetime.strptime(dates[0], '%Y-%m-%d')
        date2 = datetime.strptime(dates[1], '%Y-%m-%d')
        n_jours = (date2 - date1).days
        logger.info("Planification d'un voyage de %s jours", n_jours)
    
    # Check if the station is a group name and expand it
    if station in STATION_GROUP_MAPPING:
        # This is a station group, get all individual stations
        individual_stations = STATION_GROUP_MAPPING[station]
        logger.info(
            "Extension du groupe de gares '%s' vers %d gares individuelles",
            station,
            len(individual_stations),
        )
        
        # Get trips from all stations in the group
        all_trips = []
        for individual_station in individual_stations:
            station_trips = find_optimal_destinations_single_station(individual_station, date1, date2)
            all_trips.extend(station_trips)
        
        # Sort by time at destination (descending)
        all_trips.sort(key=lambda x: x['time_at_destination_minutes'], reverse=True)
        return all_trips
    else:
        # This is an individual station
        return find_optimal_destinations_single_station(station, date1, date2)


def find_optimal_destinations_single_station(station, date1, date2):
    """Find optimal destinations for round trips from a single station on specified dates."""
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
    logger.debug("Requête formatée : %s", formatted_query)


def get_trip_connections(dates, origins, destinations, max_connections=0, allow_station_groups=True):
    # Expand "ILE DE FRANCE" to the list of cities
    origins = expand_station_groups(origins)
    destinations = expand_station_groups(destinations)
    
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

    # Build the parameters dictionary
    params = {'max_connections': max_connections}

    # Add origins to params
    for i, origin in enumerate(origins):
        params[f'origin_{i}'] = origin

    # Add destinations to params
    for i, destination in enumerate(destinations):
        params[f'destination_{i}'] = destination

    # Add dates to params
    for i, date in enumerate(dates):
        params[f'date_{i}'] = date

    if max_connections == 0:
        # ✂️  MUCH simpler query, no recursion at all
        query = f"""
            SELECT origine, destination, heure_depart AS first_leg_departure,
                   heure_arrivee AS last_leg_arrival, uid, date
            FROM   TGVMAX
            WHERE  {origin_condition}
              AND  {destination_condition}
              AND  date IN ({date_placeholders})
              AND  DISPO='OUI' AND axe!='IC NUIT'
            ORDER  BY heure_depart;
        """
        result = run_query(query, params=params)
        
        # If no direct connections found, try with 1 connection
        if len(result) == 0:
            logger.info("No direct connections found, trying with 1 connection")
            # Fall back to recursive query with max_connections = 1
            return get_trip_connections(dates, origins, destinations, max_connections=1, allow_station_groups=allow_station_groups)
        
        return _post_process_direct_trips(result)

    # Create a CTE for station groups to allow connections within groups
    station_groups_cte = ""
    station_group_condition = ""
    if allow_station_groups and STATION_GROUPS:
        # Create a simpler approach using UNION ALL for SQLite compatibility
        group_unions = []
        for group in STATION_GROUPS:
            for station_data in group["stations"]:
                if isinstance(station_data, list):
                    # New format: [station1, station2, connection_time]
                    station1, station2, connection_time = station_data[0], station_data[1], station_data[2]
                    group_unions.append(f"SELECT '{station1}' as station1, '{station2}' as station2, {connection_time} as connection_time")
                    # Also add reverse direction
                    group_unions.append(f"SELECT '{station2}' as station1, '{station1}' as station2, {connection_time} as connection_time")
                else:
                    # Old format: just station name (for backward compatibility)
                    pass  # Skip old format for now
        
        if group_unions:
            station_groups_cte = f"""
            , station_groups AS (
                {' UNION ALL '.join(group_unions)}
            )
            """
            station_group_condition = """
                OR
                -- Connection through station group: both stations are in the same group
                EXISTS (
                    SELECT 1 FROM station_groups sg 
                    WHERE sg.station1 = pr.destination AND sg.station2 = t.origine
                )
            """

    query = f"""
        WITH RECURSIVE filtered AS (
            SELECT *
            FROM TGVMAX
            WHERE date IN ({date_placeholders}) 
              AND DISPO = 'OUI' 
              AND axe != 'IC NUIT'
              AND ({origin_condition} OR {destination_condition})
        ),
        possible_routes AS (
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
            FROM filtered
            WHERE {origin_condition}

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
                CAST(
                    CASE 
                        WHEN t.origine = pr.destination THEN pr.route_description || ' -> ' || t.destination
                        ELSE pr.route_description || ' -> ' || t.origine || ' -> ' || t.destination
                    END AS TEXT
                ) AS route_description,
                CAST(pr.route_uid || '-' || t.uid AS TEXT) AS route_uid
            FROM filtered t
            JOIN possible_routes pr
              ON (
                -- Direct connection: t.origine = pr.destination
                t.origine = pr.destination{station_group_condition}
              )
              AND (
                -- For direct connections: just check departure time is after arrival
                (t.origine = pr.destination AND t.heure_depart > pr.last_leg_arrival)
                OR
                -- For station group connections: check if there's enough time for the transfer
                (t.origine != pr.destination AND 
                 EXISTS (
                   SELECT 1 FROM station_groups sg 
                   WHERE sg.station1 = pr.destination AND sg.station2 = t.origine
                 ) AND
                 -- Calculate if there's enough time for the transfer
                 (CAST(SUBSTR(t.heure_depart, 1, 2) AS INTEGER) * 60 + CAST(SUBSTR(t.heure_depart, 4, 2) AS INTEGER)) -
                 (CAST(SUBSTR(pr.last_leg_arrival, 1, 2) AS INTEGER) * 60 + CAST(SUBSTR(pr.last_leg_arrival, 4, 2) AS INTEGER)) >= 
                 (SELECT connection_time FROM station_groups sg 
                  WHERE sg.station1 = pr.destination AND sg.station2 = t.origine LIMIT 1)
                )
              )
              AND t.date = pr.date
            WHERE pr.connection_count < :max_connections
        ){station_groups_cte}
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

    # Preview the query (optional)
    preview_query(query, params)

    # Run the query
    result = run_query(query, params=params)
    logger.info("Nombre de résultats trouvés : %d", len(result))

    # Only increase max_connections if no results found and user didn't specify a limit
    if len(result) == 0 and max_connections == 0:
        params['max_connections'] = 1
        logger.info(
            "Augmentation du nombre maximum de connexions à %d", params['max_connections']
        )
        result = run_query(query, params=params)
        
        # Continue increasing until results found or limit reached
        while len(result) == 0 and params['max_connections'] < 5:
            params['max_connections'] += 1
            logger.info(
                "Augmentation du nombre maximum de connexions à %d",
                params['max_connections'],
            )
            result = run_query(query, params=params)
    elif len(result) == 0 and max_connections > 0:
        # If we're already trying with connections but found none, try with more
        params['max_connections'] = max_connections + 1
        if params['max_connections'] <= 5:
            logger.info(
                "Augmentation du nombre maximum de connexions à %d",
                params['max_connections'],
            )
            result = run_query(query, params=params)

    # Process results for recursive queries
    result_list = []
    for index, route in result.iterrows():
        trains = list(map(int, route['route_uid'].split('-')))
        train_dic = {}
        train_dic['train_list'] = []
        prev_station = None
        for index_train, train in enumerate(trains):
            query = """
            SELECT origine, heure_depart, destination, heure_arrivee, train_no
            FROM TGVMAX
            WHERE "UID"=:uid
            """
            params = {"uid": train}
            train_info = list(run_query(query, params=params).values[0])
            # Si ce n'est pas le premier train, vérifier s'il y a un transfert de groupe
            if prev_station is not None and train_info[0] != prev_station:
                # Vérifier si prev_station et train_info[0] sont dans le même groupe
                if are_stations_in_same_group(prev_station, train_info[0]):
                    # Obtenir le temps de connexion pour le message d'avertissement
                    connection_time = get_station_connection_time(prev_station, train_info[0])
                    # Insérer une connexion virtuelle avec le format approprié et le temps de connexion
                    virtual_leg = [prev_station, '', train_info[0], '', 'Correspondance', connection_time]
                    train_dic['train_list'].append(virtual_leg)
            train_dic['train_list'].append(train_info)
            prev_station = train_info[2]  # destination
        train_dic['route_name'] = route['route_description']
        
        # Calculate total duration by considering all train segments and waiting times
        total_duration = timedelta()
        current_time = None
        filtered_train_list = []
        last_real_destination = None
        for train_info in train_dic['train_list']:
            if len(train_info) >= 5 and train_info[4] != 'Correspondance':
                # Regular train segment
                departure_str = train_info[1]
                arrival_str = train_info[3]
                if departure_str and arrival_str:
                    departure_time = datetime.strptime(departure_str, '%H:%M')
                    arrival_time = datetime.strptime(arrival_str, '%H:%M')
                    # If this is not the first train, add waiting time between trains
                    if current_time is not None:
                        if departure_time < current_time:
                            departure_time += timedelta(days=1)
                        waiting_time = departure_time - current_time
                        total_duration += waiting_time
                    
                    # Si ce segment arrive après minuit, on arrête l'itinéraire ici
                    if arrival_time < departure_time:
                        # On ajoute la durée complète jusqu'à l'arrivée réelle
                        arrival_time += timedelta(days=1)
                        train_duration = arrival_time - departure_time
                        total_duration += train_duration
                        filtered_train_list.append(list(train_info))
                        last_real_destination = train_info[2]
                        break
                    # Add train travel time
                    train_duration = arrival_time - departure_time
                    total_duration += train_duration
                    current_time = arrival_time
                filtered_train_list.append(list(train_info))
                last_real_destination = train_info[2]
            else:
                filtered_train_list.append(list(train_info))
        # Vérifier que la dernière gare atteinte est bien la destination demandée
        if last_real_destination is not None and last_real_destination != route['destination']:
            continue  # Ne pas inclure cet itinéraire
        train_dic['train_list'] = filtered_train_list
        train_dic['duration'] = format_duration(total_duration)
        train_dic['date'] = route['date']
        result_list.append(train_dic)

    # Sort results by departure time (earliest first)
    def get_departure_datetime(result):
        """Extract departure date and time for sorting"""
        from datetime import datetime
        try:
            # Get the first train's departure time
            if result['train_list'] and len(result['train_list']) > 0:
                first_train = result['train_list'][0]
                if len(first_train) >= 2 and first_train[1]:  # has departure time
                    departure_time = first_train[1]  # format: "HH:MM"
                    date_str = result.get('date', '2025-01-01')  # fallback date
                    datetime_str = f"{date_str} {departure_time}"
                    return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            # Fallback: use a very late time if no departure time found
            return datetime.strptime('2099-12-31 23:59', '%Y-%m-%d %H:%M')
        except (ValueError, KeyError, IndexError):
            # Fallback for any parsing errors
            return datetime.strptime('2099-12-31 23:59', '%Y-%m-%d %H:%M')

    result_list.sort(key=get_departure_datetime)
    return result_list

def _post_process_direct_trips(result):
    """Post-process direct trip results (no connections)"""
    result_list = []
    for index, route in result.iterrows():
        train_dic = {}
        train_dic['train_list'] = []
        
        # Get train details
        query = """
        SELECT origine, heure_depart, destination, heure_arrivee, train_no
        FROM TGVMAX
        WHERE "UID"=:uid
        """
        params = {"uid": route['UID']}
        train_info = list(run_query(query, params=params).values[0])
        train_dic['train_list'].append(train_info)
        
        # Calculate duration
        departure_str = train_info[1]
        arrival_str = train_info[3]
        if departure_str and arrival_str:
            departure_time = datetime.strptime(departure_str, '%H:%M')
            arrival_time = datetime.strptime(arrival_str, '%H:%M')
            if arrival_time < departure_time:
                arrival_time += timedelta(days=1)
            train_duration = arrival_time - departure_time
            train_dic['duration'] = format_duration(train_duration)
        else:
            train_dic['duration'] = '0m'
        
        train_dic['route_name'] = f"{route['origine']} -> {route['destination']}"
        train_dic['date'] = route.get('date', '')
        result_list.append(train_dic)
    
    # Sort results by departure time (earliest first)
    def get_departure_datetime(result):
        """Extract departure date and time for sorting"""
        from datetime import datetime
        try:
            # Get the first train's departure time
            if result['train_list'] and len(result['train_list']) > 0:
                first_train = result['train_list'][0]
                if len(first_train) >= 2 and first_train[1]:  # has departure time
                    departure_time = first_train[1]  # format: "HH:MM"
                    date_str = result.get('date', '2025-01-01')  # fallback date
                    datetime_str = f"{date_str} {departure_time}"
                    return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            # Fallback: use a very late time if no departure time found
            return datetime.strptime('2099-12-31 23:59', '%Y-%m-%d %H:%M')
        except (ValueError, KeyError, IndexError):
            # Fallback for any parsing errors
            return datetime.strptime('2099-12-31 23:59', '%Y-%m-%d %H:%M')

    result_list.sort(key=get_departure_datetime)
    return result_list
def load_station_groups():
    """Load station groups from the JSON file."""
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'station_groups.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("Avertissement : station_groups.json introuvable à %s", json_path)
        return []
    except json.JSONDecodeError as e:
        logger.error("Erreur lors de l'analyse de station_groups.json : %s", e)
        return []

# Load station groups
STATION_GROUPS = load_station_groups()

# Create a mapping from group names to station lists for quick lookup
STATION_GROUP_MAPPING = {}
for group in STATION_GROUPS:
    stations = []
    for station_data in group["stations"]:
        if isinstance(station_data, list):
            # New format: [station1, station2, connection_time]
            stations.extend([station_data[0], station_data[1]])
        else:
            # Old format: just station name
            stations.append(station_data)
    STATION_GROUP_MAPPING[group["group"]] = list(set(stations))  # Remove duplicates

# Create a reverse mapping from station to group for quick lookup
STATION_TO_GROUP_MAPPING = {}
for group in STATION_GROUPS:
    for station_data in group["stations"]:
        if isinstance(station_data, list):
            # New format: [station1, station2, connection_time]
            STATION_TO_GROUP_MAPPING[station_data[0]] = group["group"]
            STATION_TO_GROUP_MAPPING[station_data[1]] = group["group"]
        else:
            # Old format: just station name
            STATION_TO_GROUP_MAPPING[station_data] = group["group"]

def get_station_group(station):
    """Get the group name for a given station, or None if not in any group."""
    return STATION_TO_GROUP_MAPPING.get(station)

def are_stations_in_same_group(station1, station2):
    """Check if two stations belong to the same group."""
    group1 = get_station_group(station1)
    group2 = get_station_group(station2)
    return group1 is not None and group1 == group2

def get_station_connection_time(station1, station2):
    """Get the minimum connection time between two stations in the same group, or None if not in same group."""
    if not are_stations_in_same_group(station1, station2):
        return None
    
    group_name = get_station_group(station1)
    for group in STATION_GROUPS:
        if group["group"] == group_name:
            for station_data in group["stations"]:
                if isinstance(station_data, list):
                    # New format: [station1, station2, connection_time]
                    if (station_data[0] == station1 and station_data[1] == station2) or \
                       (station_data[0] == station2 and station_data[1] == station1):
                        return station_data[2]  # Return connection time in minutes
    return None

def expand_station_groups(cities_list):
    """Expand station group names to the list of individual stations."""
    if not cities_list:
        return cities_list
    
    expanded_list = []
    for city in cities_list:
        if city in STATION_GROUP_MAPPING:
            # Add all stations in the group
            expanded_list.extend(STATION_GROUP_MAPPING[city])
        else:
            expanded_list.append(city)
    
    return expanded_list

# Keep the old function for backward compatibility
def expand_ile_de_france(cities_list):
    """Expand 'ILE DE FRANCE' to the list of Île-de-France cities/stations."""
    return expand_station_groups(cities_list)


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
        print(f"DESTINATIONS OPTIMALES DEPUIS {origins[0].upper()} LE {dates}")
        print(f"{'='*100}")
        
        # Create table header with better spacing
        print(f"{'Destination':<25} {'Aller':<20} {'Retour':<20} {'Temps Total':<15} {'Temps à Dest':<15}")
        print(f"{'':<25} {'Départ-Arrivée':<20} {'Départ-Arrivée':<20} {'Voyage':<15} {'(h:min)':<15}")
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
        print(f"Trouvé {len(trips)} destination(s) optimale(s)")
    else:
        print("Aucune destination optimale trouvée pour les critères donnés.")
    
    # print(get_trip_connections(dates, origins, destinations))
