import json  # Import the json module
from sqlalchemy import create_engine, MetaData, Table, Column, ForeignKey, Integer, text
from sqlalchemy.schema import DropTable, CreateTable
from sqlalchemy import inspect
from sqlalchemy.sql import select


# Load the structure JSON file
def create_foreign_keys(parent, children, metadata, engine):
    parent_table = Table(parent, metadata, autoload_with=engine)
    parent_table_name = parent_table.name

    for child in children:
        child_table = Table(child, metadata, autoload_with=engine, extend_existing=True)

        # Check if foreign key already exists
        inspector = inspect(engine)
        foreign_keys = inspector.get_foreign_keys(child)

        # Only drop and recreate if no foreign key exists
        if not foreign_keys:
            print(f"Recreating table {child} to add foreign key to {parent}")

            # Get existing columns and data
            with engine.connect() as conn:
                data = conn.execute(select(child_table)).fetchall()  # Backup the existing data

            columns = [col.copy() for col in child_table.columns]  # Preserve original columns

            # Drop existing child table
            with engine.begin() as conn:
                conn.execute(DropTable(child_table))

                # Add parent_id as a new foreign key column
                new_columns = columns + [Column('parent_id', Integer, ForeignKey(f'{parent_table_name}.id'))]

                # Recreate the child table with the foreign key
                new_child_table = Table(
                    child,
                    metadata,
                    *new_columns,
                    extend_existing=True  # Ensure we don't re-define the table
                )
                conn.execute(CreateTable(new_child_table))

                # Insert old data back into the new table
                if data:
                    conn.execute(new_child_table.insert(), [dict(row) for row in data])
        else:
            print(f"Foreign key from {child} to {parent} already exists.")


def process_structure(data, engine, parent=None):
    metadata = MetaData()
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON;"))  # Use `text()` to wrap the SQL command

    for key, value in data.items():
        if isinstance(value, list):
            if parent is not None:
                create_foreign_keys(parent, value, metadata, engine)
            for child in value:
                process_structure({child: data.get(child, {})}, engine, key)


if __name__ == "__main__":
    structure_file = "/home/julien/Documents/pythonProjects/data/structure.json"
    db_file = "/home/julien/Documents/pythonProjects/data/formated_cp.db"

    # Open and load the JSON file
    with open(structure_file) as f:
        structure = json.load(f)

    engine = create_engine(f'sqlite:///{db_file}')

    process_structure(structure, engine)