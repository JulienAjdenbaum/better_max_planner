import json
import sqlite3
import os

def update_table_links(structure, cursor):
    """
    Update SQLite table to add foreign key constraints based on the structure.
    - Tables with 'parent_id' will be linked to their parent.
    - 'ref' tables will be linked to their referenced table.
    """
    for parent, children in structure.items():
        # Add parent-child relationship based on 'parent_id'
        if 'parent_id' in get_columns(cursor, parent):
            # Assuming each table has 'id' as the primary key
            for child in children:
                if 'id' in get_columns(cursor, child):
                    print(f"Linking {child}.parent_id to {parent}.id")
                    cursor.execute(f"""
                        ALTER TABLE {child}
                        ADD CONSTRAINT fk_{child}_{parent}
                        FOREIGN KEY (parent_id)
                        REFERENCES {parent}(id)
                    """)

        # Handle 'ref' tables, which link to another table via a 'ref' column
        if parent.endswith('ref'):
            ref_table = parent[:-4]  # Assume the referenced table has the same name without '_ref'
            if 'ref' in get_columns(cursor, parent) and 'id' in get_columns(cursor, ref_table):
                print(f"Linking {parent}.ref to {ref_table}.id")
                cursor.execute(f"""
                    ALTER TABLE {parent}
                    ADD CONSTRAINT fk_{parent}_{ref_table}
                    FOREIGN KEY (ref)
                    REFERENCES {ref_table}(id)
                """)


def get_columns(cursor, table_name):
    """
    Get the column names for a specific table in the SQLite database.
    """
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [info[1] for info in cursor.fetchall()]


if __name__ == "__main__":
    db_file = "../../data/"
    # Load the structure from the JSON file
    with open('structure.json', 'r') as f:
        structure = json.load(f)

    # Connect to your SQLite database
    conn = sqlite3.connect('your_database.db')
    cursor = conn.cursor()
    # Update the tables based on the structure
    update_table_links(structure, cursor)

    # Commit and close the connection
    conn.commit()
    conn.close()
