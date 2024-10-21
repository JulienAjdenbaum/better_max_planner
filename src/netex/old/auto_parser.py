import os
import xml.etree.ElementTree as ET
import logging
from sqlalchemy import create_engine, Column, Integer, Float, String, Text, MetaData, Table, select
from sqlalchemy.orm import sessionmaker, declarative_base
from collections import defaultdict
import re
import copy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
Base = declarative_base()
models = {}  # To store dynamically created models
element_structure = {}  # To store element structures
parent_relations = {}  # To store parent-child relationships

def determine_column_type(value):
    """Determine the SQLAlchemy column type based on the value."""
    if value is None or value == '':
        return String  # Default to String if value is empty
    # Try to determine if it's an Integer
    if re.match(r'^-?\d+$', value):
        return Integer
    # Try to determine if it's a Float
    if re.match(r'^-?\d+\.\d*$', value):
        return Float
    # Otherwise, treat as String
    return String

def analyze_structure(element, parent_tag=None):
    """
    Recursively analyze the XML structure to collect data types and parent-child relationships.
    """
    tag = element.tag.split('}')[-1]  # Remove namespace if present

    # Initialize structure for the tag if not already present
    if tag not in element_structure:
        element_structure[tag] = {
            'attributes': {},
            'text': False  # Indicates if element has text content
        }

    structure = element_structure[tag]

    # Process attributes
    for attr_name, attr_value in element.attrib.items():
        col_type = determine_column_type(attr_value)
        structure['attributes'][attr_name] = col_type

    # Check if element has text content
    if element.text and element.text.strip():
        structure['text'] = True

    # Record parent-child relationship
    if parent_tag:
        if tag not in parent_relations:
            parent_relations[tag] = set()
        parent_relations[tag].add(parent_tag)

    # Recurse into children
    for child in element:
        analyze_structure(child, parent_tag=tag)

def create_model_class(tag, structure):
    """Dynamically create a SQLAlchemy model class."""
    if tag in models:
        return models[tag]

    attrs = {
        '__tablename__': tag.lower(),
    }

    # Determine if 'id' attribute exists and use it as primary key
    if 'id' in structure['attributes']:
        id_type = structure['attributes']['id']
        attrs['id'] = Column(id_type, primary_key=True)
        del structure['attributes']['id']
    else:
        attrs['id'] = Column(Integer, primary_key=True, autoincrement=True)

    # Add other attributes as columns
    for attr_name, col_type in structure['attributes'].items():
        attrs[attr_name] = Column(col_type)

    # Add text content as a column if applicable
    if structure['text']:
        attrs['text'] = Column(String)

    # Add parent_id column as String
    attrs['parent_id'] = Column(String)

    # Create the model class
    model = type(tag, (Base,), attrs)
    models[tag] = model
    logger.info(f"Created model for table: {tag.lower()}")
    return model


def process_element(element, session, parent_instance=None):
    """
    Recursively process XML elements and store their data in the database.

    Parameters:
    - element: the current XML element being processed
    - session: the active SQLAlchemy session
    - parent_instance: the parent instance, used to set the parent_id for child elements
    """
    # Extract the tag name and remove namespaces if present
    tag = element.tag.split('}')[-1]

    # Get the element structure
    structure = element_structure.get(tag)
    if not structure:
        logger.warning(f"No structure found for tag: {tag}")
        return

    # Use the existing model class for the current tag
    ModelClass = models.get(tag)
    if not ModelClass:
        logger.error(f"No model found for tag: {tag}")
        return

    # Prepare data for the current element
    data = {}

    # Process attributes and store them in data
    for attr_name in structure['attributes'].keys():
        data[attr_name] = element.attrib.get(attr_name)

    # Process unique child elements as columns (one-to-one relationships)
    for col_name in structure['columns'].keys():
        child = element.find(f'./{col_name}')
        if child is not None:
            data[col_name] = child.text.strip() if child.text else None

    # Add parent_id if applicable (linking child to its parent)
    if parent_instance:
        data['parent_id'] = getattr(parent_instance, 'id')

    # Create an instance of the model and add it to the session
    instance = ModelClass(**data)
    session.add(instance)
    session.flush()  # To get the instance ID for future parent references

    # Process child elements that are represented as tables (one-to-many relationships)
    for table_tag in structure['tables']:
        for child in element.findall(f'./{table_tag}'):
            process_element(child, session, parent_instance=instance)

    # Commit the session after processing all elements
    session.commit()


def remove_empty_columns_and_useless_tables(engine):
    """Remove empty columns and merge tables that can be represented as columns in parent tables."""
    metadata = MetaData()
    metadata.reflect(bind=engine)
    conn = engine.connect()

    # Identify empty columns
    for table_name, table in metadata.tables.items():
        logger.info(f"Checking for empty columns in table: {table_name}")
        empty_columns = []
        for column in table.columns:
            # Skip primary key columns
            if column.primary_key:
                continue
            # Check if the column is entirely NULL or empty strings
            sel = select([column]).where(column != None).where(column != '').limit(1)
            result = conn.execute(sel).fetchone()
            if result is None:
                empty_columns.append(column.name)
                logger.info(f"Column '{column.name}' is empty and will be removed from table '{table_name}'")

        if empty_columns:
            # Recreate the table without empty columns
            recreate_table_without_columns(engine, table_name, empty_columns)

    # Identify and merge useless tables starting from leaf nodes
    ordered_tags = get_ordered_tags()
    for tag in ordered_tags:
        table = metadata.tables.get(tag.lower())
        if not table:
            continue

        # Check if table can be merged into parent table
        can_merge = can_merge_table(conn, table)
        if can_merge:
            merge_table_into_parent(engine, conn, table)

    conn.close()

def get_ordered_tags():
    """Return tags ordered from leaf nodes to root."""
    # Build a dependency graph
    graph = defaultdict(set)
    for child_tag, parents in parent_relations.items():
        for parent_tag in parents:
            graph[child_tag].add(parent_tag)

    # Perform a topological sort
    visited = set()
    ordered_tags = []

    def visit(node):
        if node not in visited:
            visited.add(node)
            for neighbor in graph.get(node, []):
                visit(neighbor)
            ordered_tags.append(node)

    for node in graph:
        visit(node)

    return ordered_tags

def can_merge_table(conn, table):
    """Determine if a table can be merged into its parent table."""
    # Get the number of rows in the table
    sel = select([func.count()]).select_from(table)
    result = conn.execute(sel).scalar()
    if result == 0:
        # Table is empty, can be dropped
        return True
    else:
        # Check if each row has a unique parent_id
        sel = select([table.c.parent_id, func.count()]).group_by(table.c.parent_id)
        results = conn.execute(sel).fetchall()
        for parent_id, count in results:
            if count > 1:
                # Multiple rows for the same parent, cannot merge
                return False
        return True

def merge_table_into_parent(engine, conn, child_table):
    """Merge child table into its parent table."""
    metadata = MetaData()
    metadata.reflect(bind=engine)
    child_table_name = child_table.name
    child_columns = [col for col in child_table.columns if col.name not in ('id', 'parent_id')]

    # Get parent table name from parent_relations
    parent_tags = parent_relations.get(child_table_name.capitalize(), [])
    if not parent_tags:
        # No parent, cannot merge
        return

    parent_tag = list(parent_tags)[0]  # Assume single parent
    parent_table = metadata.tables.get(parent_tag.lower())
    if not parent_table:
        logger.warning(f"Parent table '{parent_tag.lower()}' not found for '{child_table_name}'")
        return

    # Add child columns to parent table
    for col in child_columns:
        if col.name not in parent_table.c:
            col_copy = copy.deepcopy(col)
            parent_table.append_column(col_copy)
            # Alter table to add the new column
            engine.execute(f'ALTER TABLE "{parent_table.name}" ADD COLUMN "{col.name}"')

    # Update parent table with data from child table
    sel = select([child_table.c.parent_id] + child_columns)
    results = conn.execute(sel).fetchall()
    for row in results:
        parent_id = row['parent_id']
        update_values = {col.name: row[col.name] for col in child_columns}
        upd = parent_table.update().where(parent_table.c.id == parent_id).values(**update_values)
        conn.execute(upd)

    # Drop the child table
    child_table.drop(engine)
    logger.info(f"Merged table '{child_table_name}' into '{parent_table.name}' and dropped '{child_table_name}'")

def recreate_table_without_columns(engine, table_name, columns_to_remove):
    """Recreate a table without specified columns."""
    metadata = MetaData()
    metadata.reflect(bind=engine)
    old_table = metadata.tables[table_name]

    # Define new table schema
    new_columns = [c.copy() for c in old_table.columns if c.name not in columns_to_remove]
    new_table = Table(f"{table_name}_new", metadata, *new_columns)

    # Create the new table
    new_table.create(bind=engine)
    logger.info(f"Created new table '{new_table.name}' without columns: {columns_to_remove}")

    # Copy data from old table to new table
    columns_to_copy = [c.name for c in new_columns]
    insert_stmt = new_table.insert().from_select(columns_to_copy, select([old_table.c[name] for name in columns_to_copy]))
    engine.execute(insert_stmt)
    logger.info(f"Copied data from '{table_name}' to '{new_table.name}'")

    # Drop the old table
    old_table.drop(bind=engine)
    logger.info(f"Dropped old table '{table_name}'")

    # Rename new table to old table's name
    engine.execute(f'ALTER TABLE "{new_table.name}" RENAME TO "{table_name}"')
    logger.info(f"Renamed '{new_table.name}' to '{table_name}'")

def process_xml_files(directory, db_path):
    # Erase old database if exists and create a new one
    if os.path.exists(db_path):
        logger.info(f"Deleting old database at {db_path}")
        os.remove(db_path)
    else:
        logger.info(f"Creating new database at {db_path}")

    # Set up the database engine
    engine = create_engine(f'sqlite:///{db_path}')
    Session = sessionmaker(bind=engine)
    session = Session()

    global element_structure
    element_structure = {}
    global parent_relations
    parent_relations = {}

    # First pass: Analyze structure and collect data types
    for filename in os.listdir(directory):
        if filename.endswith(".xml"):
            xml_file = os.path.join(directory, filename)
            logger.info(f"Analyzing XML file: {xml_file}")
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                analyze_structure(root)
            except Exception as e:
                logger.error(f"Failed to analyze {xml_file}: {e}")

    # Create models for all elements
    for tag, structure in element_structure.items():
        create_model_class(tag, structure)

    # Now that all models are created, create tables
    Base.metadata.create_all(engine)
    logger.info(f"Database created successfully at {db_path}")

    # Second pass: Process elements and populate database
    for filename in os.listdir(directory):
        if filename.endswith(".xml"):
            xml_file = os.path.join(directory, filename)
            logger.info(f"Processing XML file: {xml_file}")
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                process_element(root, session)
                session.commit()
                logger.info(f"Successfully processed {xml_file}")
            except Exception as e:
                logger.error(f"Failed to process {xml_file}: {e}")
                session.rollback()
    logger.info("All XML files have been processed.")

    # Remove empty columns and merge tables
    remove_empty_columns_and_useless_tables(engine)
    logger.info("Empty columns have been removed and tables have been merged where applicable.")


if __name__ == "__main__":
    # Prompt the user for the directory to save the database
    db_path = "/data/new.db"

    # Directory containing XML files
    xml_directory = "/home/julien/Documents/pythonProjects/data/netex_xml"

    logger.info(f"Starting XML processing for directory: {xml_directory}")
    process_xml_files(xml_directory, db_path)
    logger.info("XML processing completed.")
