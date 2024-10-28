from venv import logger

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, declarative_base
import logging
import json
import os
import time

Base = declarative_base()

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
def get_parent_tables(table_name, structure):
    """Retrieve the parent table based on the structure.json relationships."""
    parents = []
    for parent, children in structure.items():
        if table_name in children:
            parents.append(parent)
    if parents == []:
        return None
    return parents


# Check if parent_id is unique in the table
def check_unique_parents(table_name, engine):
    query_text = f"""
        SELECT parent_id, COUNT(*)
        FROM {table_name}
        GROUP BY parent_id
        HAVING COUNT(*) > 1
    """
    with engine.connect() as conn:
        result = conn.execute(sa.text(query_text)).fetchone()
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
        for col in child_columns if col['name'] not in ['parent_id',
                                                        'id'] and f"{parent_table.lower()}_{child_table.lower()}_{col['name']}" not in parent_column_names
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
    parents = get_parent_tables(table_to_drop, structure)
    print(table_to_drop, parents)
    for parent in parents:
        structure[parent].remove(table_to_drop)
        if table_to_drop in structure.keys():
            if list(set(structure[parent]) & set(structure[table_to_drop])) != []:
                print(f"Creating duplicates for tables {list(set(structure[parent]) & set(structure[table_to_drop]))}")
            structure[parent] = list(set(structure[parent]) | set(structure[table_to_drop]))
    if table_to_drop in structure.keys():     del structure[table_to_drop]
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
        for table in table_names:  # run though every table, find their parents and their child
            print(f"\nWorking on table {table}")
            parent_tables = get_parent_tables(table, structure)
            if parent_tables is None:
                print(f"{table} has no parents.")
                continue
            print(f"{table} has parents {parent_tables}")
            table_has_unique_parents = check_unique_parents(table, engine)
            if table_has_unique_parents and table not in dropped_tables:
                print(f"Table parents are unique")
                for parent_table in parent_tables:
                    print(f"working on parent {parent_table}")
                    if table in dropped_tables:
                        print(f"Table in dropped tables")
                    if parent_table:
                        print()
                        # Update child tables to point to the parent of the current table
                        if table in structure.keys():
                            print()
                            print("children:", structure[table])
                            for child_table in structure[table]:
                                print(child_table, table, parent_table)
                                update_child_parent_id(child_table, table, parent_table, engine)
                        else:
                            print(f"Table {table} is a leaf")
                        try:
                            move_columns_to_parent(table, parent_table, engine)
                            logging.info(f"Table '{table}' merged into '{parent_table}'.")
                        except Exception as e:
                            logging.error(f"Failed to merge '{table}' into '{parent_table}': {e}")
                            raise
                try:
                    structure = update_structure_at_drop(table, structure)
                    drop_table(table, engine)
                    print(structure)
                    dropped_tables.add(table)
                    # time.sleep(0.1)
                except Exception as e:
                    logging.error(f"Failed to merge '{table}' into '{parent_table}': {e}")
                    raise
                print()
            else:
                print(f"There are duplicate in parents")
    return structure


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    db_path = "/home/julien/Documents/pythonProjects/data/formated.db"
    structure_file = "/home/julien/Documents/pythonProjects/data/structure.json"

    # Load parent-child relationships from structure.json
    structure = load_structure(structure_file)

    if structure:
        engine, session = setup_db(db_path)

        logging.info("Starting postprocessing...")
        structure = merge_tables(engine, structure)
        logging.info("Postprocessing completed.")

    # save_parent_child_structure(structure, structure_file)
