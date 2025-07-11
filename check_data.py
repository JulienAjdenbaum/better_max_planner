#!/usr/bin/env python3
import sys
import os

# Add the current directory to the Python path so we can import utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import run_query, expand_station_groups

def check_data():
    dates = ["2025-08-07", "2025-08-08", "2025-08-09"]
    origins = ["ILE DE FRANCE (toutes gares)"]
    destinations = ["ORANGE"]
    
    # Expand the origins to see what stations we're actually looking for
    expanded_origins = expand_station_groups(origins)
    print(f"Expanded origins: {expanded_origins}")
    
    print("\n" + "="*80)
    print("CHECKING DATABASE DATA")
    print("="*80)
    
    # Check total data for these dates
    query = """
    SELECT date, COUNT(*) as total_trips
    FROM TGVMAX 
    WHERE date IN ('2025-08-07', '2025-08-08', '2025-08-09')
    GROUP BY date
    ORDER BY date
    """
    result = run_query(query)
    print("\nTotal trips available by date:")
    for _, row in result.iterrows():
        print(f"  {row['date']}: {row['total_trips']} trips")
    
    # Check data for expanded origins
    origin_placeholders = ', '.join([f"'{origin}'" for origin in expanded_origins])
    query = f"""
    SELECT date, origine, COUNT(*) as trips_from_origin
    FROM TGVMAX 
    WHERE date IN ('2025-08-07', '2025-08-08', '2025-08-09')
    AND origine IN ({origin_placeholders})
    AND DISPO = 'OUI'
    GROUP BY date, origine
    ORDER BY date, origine
    """
    result = run_query(query)
    print(f"\nTrips from Île-de-France stations (available):")
    for _, row in result.iterrows():
        print(f"  {row['date']} - {row['origine']}: {row['trips_from_origin']} trips")
    
    # Check data for destination
    query = """
    SELECT date, destination, COUNT(*) as trips_to_destination
    FROM TGVMAX 
    WHERE date IN ('2025-08-07', '2025-08-08', '2025-08-09')
    AND destination = 'ORANGE'
    AND DISPO = 'OUI'
    GROUP BY date, destination
    ORDER BY date
    """
    result = run_query(query)
    print(f"\nTrips to ORANGE (available):")
    for _, row in result.iterrows():
        print(f"  {row['date']} - {row['destination']}: {row['trips_to_destination']} trips")
    
    # Check direct connections from Île-de-France to ORANGE
    query = f"""
    SELECT date, origine, destination, heure_depart, heure_arrivee, DISPO
    FROM TGVMAX 
    WHERE date IN ('2025-08-07', '2025-08-08', '2025-08-09')
    AND origine IN ({origin_placeholders})
    AND destination = 'ORANGE'
    AND DISPO = 'OUI'
    ORDER BY date, heure_depart
    LIMIT 10
    """
    result = run_query(query)
    print(f"\nDirect connections from Île-de-France to ORANGE:")
    if len(result) > 0:
        for _, row in result.iterrows():
            print(f"  {row['date']} - {row['origine']} → {row['destination']}: {row['heure_depart']}-{row['heure_arrivee']}")
    else:
        print("  No direct connections found")
    
    # Check what destinations are available from Île-de-France
    query = f"""
    SELECT DISTINCT destination, COUNT(*) as trip_count
    FROM TGVMAX 
    WHERE date IN ('2025-08-07', '2025-08-08', '2025-08-09')
    AND origine IN ({origin_placeholders})
    AND DISPO = 'OUI'
    GROUP BY destination
    ORDER BY trip_count DESC
    LIMIT 20
    """
    result = run_query(query)
    print(f"\nTop 20 destinations from Île-de-France:")
    for _, row in result.iterrows():
        print(f"  {row['destination']}: {row['trip_count']} trips")

if __name__ == "__main__":
    check_data() 