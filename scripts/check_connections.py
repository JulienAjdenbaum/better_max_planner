#!/usr/bin/env python3
from sqlalchemy import create_engine, text

engine = create_engine('sqlite:///tgvmax.db')

# Check direct connections
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM TGVMAX 
        WHERE date = '2025-07-12' 
        AND origine = 'PARIS (intramuros)' 
        AND destination = 'LYON (intramuros)' 
        AND DISPO = 'OUI'
    """))
    direct_count = result.fetchone()[0]
    print(f"Direct connections PARIS → LYON: {direct_count}")

# Check any connections to LYON
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM TGVMAX 
        WHERE date = '2025-07-12' 
        AND destination = 'LYON (intramuros)' 
        AND DISPO = 'OUI'
    """))
    total_count = result.fetchone()[0]
    print(f"Total connections to LYON: {total_count}")

# Check any connections from PARIS
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM TGVMAX 
        WHERE date = '2025-07-12' 
        AND origine = 'PARIS (intramuros)' 
        AND DISPO = 'OUI'
    """))
    paris_count = result.fetchone()[0]
    print(f"Total connections from PARIS: {paris_count}")

# Show some sample direct connections from PARIS
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT origine, destination, heure_depart, heure_arrivee, DISPO
        FROM TGVMAX 
        WHERE date = '2025-07-12' 
        AND origine = 'PARIS (intramuros)' 
        AND DISPO = 'OUI'
        LIMIT 5
    """))
    print(f"\nSample direct connections from PARIS:")
    for row in result:
        print(f"  {row[0]} → {row[1]} ({row[2]}-{row[3]}) - {row[4]}") 