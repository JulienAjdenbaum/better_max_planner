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
        AND destination = 'AVIGNON TGV' 
        AND DISPO = 'OUI'
    """))
    direct_count = result.fetchone()[0]
    print(f"Direct connections PARIS → AVIGNON TGV: {direct_count}")

# Check any connections to AVIGNON TGV
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM TGVMAX 
        WHERE date = '2025-07-12' 
        AND destination = 'AVIGNON TGV' 
        AND DISPO = 'OUI'
    """))
    total_count = result.fetchone()[0]
    print(f"Total connections to AVIGNON TGV: {total_count}")

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