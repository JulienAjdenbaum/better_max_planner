from venv import logger

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, declarative_base
import logging
import json
import os

Base = declarative_base()

def save_parent_child_structure(parent_child_structure, structure_file):
    """Save the parent-child structure to a JSON file."""
    with open(structure_file, 'w') as f:
        json.dump(parent_child_structure, f, indent=4)
    logging.info(f"Parent-child structure saved to {structure_file}")


# Load the parent-child structure from the structure.json file
def load_structure(structure_file):
    if os.path.exists(structure_file):
        with open(structure_file, 'r') as f:
            return {key.lower(): [value.lower() for value in values] for key, values in json.load(f).items()}
    else:
        logging.error(f"Structure file {structure_file} not found.")
        return {}

# Set up the database engine and session
def setup_db(db_path):
    """Set up the database engine and session."""
    engine = sa.create_engine(f'sqlite:///{db_path}')
    Session = sessionmaker(bind=engine)
    session = Session()
    return engine, session

# Retrieve all table names from the database
def get_all_table_names(engine):
    inspector = sa.inspect(engine)
    return inspector.get_table_names()

# Use structure.json to get the parent table of a given table
def get_parent_table(table_name, structure):
    """Retrieve the parent table based on the structure.json relationships."""
    for parent, children in structure.items():
        if table_name in children:
            return parent
    return None

# Check if parent_id is unique in the table
def check_unique_parents(table_name, engine):
    query = sa.text(f"""
        SELECT parent_id, COUNT(*)
        FROM {table_name}
        GROUP BY parent_id
        HAVING COUNT(*) > 1
    """)
    with engine.connect() as conn:
        result = conn.execute(query).fetchone()
        return result is None  # No duplicates means the table can be merged

# Map SQLAlchemy types to SQLite types
def map_sqlalchemy_type_to_sqlite(col_type):
    if isinstance(col_type, sa.Integer):
        return "INTEGER"
    elif isinstance(col_type, sa.Float):
        return "REAL"
    elif isinstance(col_type, (sa.String, sa.Text)):
        return "TEXT"
    return "TEXT"

# Move columns from the child table to the parent table
def move_columns_to_parent(child_table, parent_table, engine):
    """Move columns from the child table to the parent table with renamed columns."""
    inspector = sa.inspect(engine)
    child_columns = inspector.get_columns(child_table)
    parent_columns = inspector.get_columns(parent_table)

    parent_column_names = {col['name'] for col in parent_columns}
    columns_to_add = {
        f"{parent_table.lower()}_{child_table.lower()}_{col['name']}": (col['name'], col['type'])
        for col in child_columns if col['name'] not in ['parent_id', 'id'] and f"{parent_table.lower()}_{child_table.lower()}_{col['name']}" not in parent_column_names
    }

    with engine.connect() as conn:
        for new_col_name, (col_name, col_type) in columns_to_add.items():
            sqlite_type = map_sqlalchemy_type_to_sqlite(col_type)
            query_text = f"ALTER TABLE {parent_table} ADD COLUMN {new_col_name} {sqlite_type}"
            try:
                conn.execute(sa.text(query_text))
                conn.commit()
                logging.info(f"Added column '{new_col_name}' to table '{parent_table}' with type '{sqlite_type}'.")
            except sa.exc.OperationalError as e:
                logging.error(f"Failed to add column '{new_col_name}' to '{parent_table}': {e}")

        if columns_to_add:
            column_updates = [
                f"{new_col} = (SELECT {child_table}.{original_col} FROM {child_table} WHERE {child_table}.parent_id = {parent_table}.id)"
                for new_col, (original_col, _) in columns_to_add.items()
            ]
            if column_updates:
                update_query = f"""
                    UPDATE {parent_table}
                    SET {", ".join(column_updates)}
                    WHERE EXISTS (SELECT 1 FROM {child_table} WHERE {child_table}.parent_id = {parent_table}.id)
                """
                try:
                    conn.execute(sa.text(update_query))
                    conn.commit()
                    logging.info(f"Moved columns from '{child_table}' to '{parent_table}'.")
                except sa.exc.OperationalError as e:
                    logging.error(f"Failed to move columns from '{child_table}' to '{parent_table}': {e}")

# Update the parent_id of the child table to point to the new parent (grandparent)
def update_child_parent_id(child_table, old_parent_table, new_parent_table, engine):
    query_text = f"""
        UPDATE {child_table}
        SET parent_id = (
            SELECT {old_parent_table}.parent_id
            FROM {old_parent_table}
            WHERE {old_parent_table}.id = {child_table}.parent_id
        )
        WHERE EXISTS (
            SELECT 1 FROM {old_parent_table}
            WHERE {old_parent_table}.id = {child_table}.parent_id
        )
    """

    with engine.connect() as conn:
        try:
            conn.execute(sa.text(query_text))
            conn.commit()
            logging.info(f"Updated parent_id in '{child_table}' to point to the parent of '{old_parent_table}'.")
        except sa.exc.OperationalError as e:
            logging.error(f"Failed to update parent_id in '{child_table}': {e}")

def update_structure_at_drop(table_to_drop, structure):
    parent = get_parent_table(table_to_drop, structure)
    if table_to_drop in structure.keys():
        structure[parent] = structure[parent] + structure[table_to_drop]
        structure[parent].remove(table_to_drop)
        del structure[table_to_drop]
    return structure

# Drop a table from the database
def drop_table(table_name, engine):
    drop_query = sa.text(f"DROP TABLE IF EXISTS {table_name}")
    with engine.connect() as conn:
        try:
            conn.execute(drop_query)
            conn.commit()
            logging.info(f"Dropped table '{table_name}'.")
        except sa.exc.OperationalError as e:
            logging.error(f"Failed to drop table '{table_name}': {e}")

# Merge tables into their parents using structure.json
def merge_tables(engine, structure):
    table_names = get_all_table_names(engine)
    dropped_tables = set()

    with engine.begin() as connection:
        for table in table_names:
            parent_table = get_parent_table(table, structure)
            if parent_table and table not in dropped_tables and check_unique_parents(table, engine):
                # Update child tables to point to the parent of the current table
                for child_table in table_names:
                    # print(get_parent_table(child_table, structure))
                    if child_table != table and get_parent_table(child_table, structure) == table:
                        update_child_parent_id(child_table, table, parent_table, engine)

                try:
                    move_columns_to_parent(table, parent_table, engine)
                    structure = update_structure_at_drop(table, structure)
                    drop_table(table, engine)
                    logging.info(f"Table '{table}' merged into '{parent_table}'.")
                    dropped_tables.add(table)
                except Exception as e:
                    logging.error(f"Failed to merge '{table}' into '{parent_table}': {e}")
                    raise
    return structure

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    db_path = "/data/formated.db"
    structure_file = "/data/structure.json"

    # Load parent-child relationships from structure.json
    structure = load_structure(structure_file)

    if structure:
        engine, session = setup_db(db_path)

        logging.info("Starting postprocessing...")
        structure = merge_tables(engine, structure)
        logging.info("Postprocessing completed.")

    save_parent_child_structure(structure, structure_file)
