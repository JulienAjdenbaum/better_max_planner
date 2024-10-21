import os
import xml.etree.ElementTree as ET
import logging
import json  # To save the structure in a reusable format
from sqlalchemy import create_engine, Column, Integer, Float, String, Index
from sqlalchemy.orm import sessionmaker, declarative_base
import re
from tqdm import tqdm  # Import tqdm for progress bars

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQLAlchemy setup
Base = declarative_base()
models = {}  # To store dynamically created models
element_structure = {}  # To store element structures
parent_child_structure = {}  # To track parent-child relationships

BATCH_SIZE = 500  # Define the batch size for bulk insertions

def determine_column_type(value):
    """Determine SQLAlchemy column type based on the value."""
    if not value:
        return String
    if re.match(r'^-?\d+$', value):
        return Integer
    if re.match(r'^-?\d+\.\d*$', value):
        return Float
    return String


def create_model(tag, structure):
    """Dynamically create SQLAlchemy model class, append '_table' to table name."""
    if tag in models:
        return models[tag]

    table_name = f"_{tag.lower()}"  # Append '_table' to ensure safe table names
    attrs = {'__tablename__': table_name}

    # Ensure the primary key is an Integer to allow autoincrement
    if 'id' in structure['attributes'] and structure['attributes']['id'] == String:
        attrs['id'] = Column(String, primary_key=True)  # Keep as String if explicitly needed
    else:
        attrs['id'] = Column(Integer, primary_key=True, autoincrement=True)  # Enable auto-increment for Integer IDs

    # Add other attributes and child elements as columns
    for attr, col_type in {**structure['attributes'], **structure['columns']}.items():
        if attr != 'id':  # Avoid redefining 'id' as a regular column
            attrs[attr] = Column(col_type)

    # Add parent_id column for relationships (as String)
    if tag != 'Root':
        attrs['parent_id'] = Column(String)

    # Index parent_id for faster lookups
    attrs['__table_args__'] = (
        Index(f'ix_{table_name}_parent_id', 'parent_id'),
    )

    model = type(tag, (Base,), attrs)
    models[tag] = model
    logger.info(f"Created model for table: {table_name}")
    return model


def analyze_element_structure(element, ns_map, parent_tag=None):
    """Recursively analyze XML structure to determine attributes, text content, and child elements."""
    tag = element.tag.split('}')[-1]  # Remove namespace if present
    if parent_tag:
        if parent_tag not in parent_child_structure:
            parent_child_structure[parent_tag + "_table"] = []
        if tag not in parent_child_structure[parent_tag + "_table"]:
            parent_child_structure[parent_tag + "_table"].append(tag + "_table")

    if tag not in element_structure:
        element_structure[tag] = {'attributes': {}, 'columns': {}, 'tables': set()}

    structure = element_structure[tag]

    # Analyze attributes
    for attr_name, attr_value in element.attrib.items():
        structure['attributes'][attr_name] = determine_column_type(attr_value)

    # Include the text content of the element as a column, if present
    if element.text and element.text.strip():
        structure['columns']['text_content'] = determine_column_type(element.text.strip())

    # Treat all child elements as potential tables (no skipping for single-child elements)
    for child in element:
        child_tag = child.tag.split('}')[-1]
        structure['tables'].add(child_tag)

    # Recursively analyze children
    for child in element:
        analyze_element_structure(child, ns_map, tag)


def process_element(element, session, ns_map, parent_instance=None, progress=None, batch=None):
    """Recursively process elements, populate the database, and include element text content."""
    tag = element.tag.split('}')[-1]
    structure = element_structure.get(tag)
    if not structure:
        logger.warning(f"No structure found for tag: {tag}")
        return

    ModelClass = models.get(tag)
    if not ModelClass:
        logger.error(f"No model found for tag: {tag}")
        return

    # Prepare data from attributes, text content, and child elements
    data = {attr: element.attrib.get(attr) for attr in structure['attributes']}

    # Handle the case where 'id' is missing and auto-generate it for Integer fields
    if 'id' not in data and 'id' in structure['attributes'] and isinstance(ModelClass.id.type, Integer):
        data['id'] = None  # Let SQLAlchemy auto-generate the ID

    data.update({col: element.find(f'./netex:{col}', ns_map).text.strip() if element.find(f'./netex:{col}', ns_map) is not None else None
                 for col in structure['columns'] if col != 'text_content'})

    # Include text content as a column, if present
    if 'text_content' in structure['columns']:
        data['text_content'] = element.text.strip() if element.text else None

    if parent_instance:
        data['parent_id'] = getattr(parent_instance, 'id')

    instance = ModelClass(**data)

    # Add to batch instead of committing each instance
    batch.append(instance)

    if len(batch) >= BATCH_SIZE:
        session.bulk_save_objects(batch)
        session.flush()
        batch.clear()

    # Process all child elements as tables
    for table_tag in structure['tables']:
        children = element.findall(f'./netex:{table_tag}', ns_map)

        # Initialize a tqdm progress bar for child elements
        for child in tqdm(children, desc=f"Processing {table_tag}", leave=False):
            process_element(child, session, ns_map, parent_instance=instance, batch=batch)

    # Update the global progress bar
    if progress is not None:
        progress.update(1)


def save_parent_child_structure(structure_file):
    """Save the parent-child structure to a JSON file."""
    with open(structure_file, 'w') as f:
        json.dump(parent_child_structure, f, indent=4)
    logging.info(f"Parent-child structure saved to {structure_file}")


def process_xml_files(directory, db_path, structure_file):
    """Main function to process XML files and populate the database."""
    if os.path.exists(db_path):
        logger.info(f"Deleting old database at {db_path}")
        os.remove(db_path)

    engine = create_engine(f'sqlite:///{db_path}')
    Session = sessionmaker(bind=engine)
    session = Session()

    global element_structure
    element_structure.clear()

    # Analyze XML structure
    for filename in filter(lambda f: f.endswith(".xml"), os.listdir(directory)):
        xml_file = os.path.join(directory, filename)
        logger.info(f"Analyzing XML file: {xml_file}")
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            # Extract the namespace from the root element dynamically
            ns_map = {'netex': root.tag[root.tag.find("{") + 1:root.tag.find("}")]}

            # Analyze element structure with namespace
            analyze_element_structure(root, ns_map)

        except Exception as e:
            logger.error(f"Failed to analyze {xml_file}: {e}")

    # Save the structure to the structure file
    save_parent_child_structure(structure_file)

    # Create models and tables
    for tag, structure in element_structure.items():
        create_model(tag, structure)

    Base.metadata.create_all(engine)
    logger.info(f"Database created at {db_path}")

    # Populate the database
    for filename in filter(lambda f: f.endswith(".xml"), os.listdir(directory)):
        xml_file = os.path.join(directory, filename)
        logger.info(f"Processing XML file: {xml_file}")
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            # Extract the namespace again for processing
            ns_map = {'netex': root.tag[root.tag.find("{") + 1:root.tag.find("}")]}

            # Initialize the tqdm progress bar for total elements
            total_elements = len(root.findall(".//*"))

            # Batch insertions
            batch = []
            with tqdm(total=total_elements, desc="Global Progress") as progress:
                process_element(root, session, ns_map, progress=progress, batch=batch)

            # Commit any remaining items in the batch
            if batch:
                session.bulk_save_objects(batch)
                session.flush()

            session.commit()
            logger.info(f"Successfully processed {xml_file}")
        except Exception as e:
            logger.error(f"Failed to process {xml_file}: {e}")
            session.rollback()

    logger.info("All XML files have been processed.")


if __name__ == "__main__":
    xml_directory = "/home/julien/Documents/pythonProjects/data/netex_xml"
    db_path = "/data/formated.db"
    structure_file = "/data/structure.json"

    logger.info(f"Starting XML processing for directory: {xml_directory}")
    process_xml_files(xml_directory, db_path, structure_file)
    logger.info("XML processing completed.")
