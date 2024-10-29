import create_db, check_completeness, clean_tables, create_links
import logging
import json
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ElementsMissing(Exception):
    pass


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


if __name__ == '__main__':
    # xml_directory = "/home/julien/Documents/pythonProjects/data/netex_xml"
    xml_directory = "/home/julien/Documents/pythonProjects/data/test_xmls"
    db_path = "/home/julien/Documents/pythonProjects/data/formated_cp.db"
    structure_file = "/home/julien/Documents/pythonProjects/data/structure.json"

    logger.info(f"Starting database cration for directory: {xml_directory}")
    structure, engine = create_db.process_xml_files(xml_directory, db_path, structure_file)
    logger.info("Databse creation completed.")

    logger.info("Starting check that all elements are present")
    elements_dict = check_completeness.get_element_dict(xml_directory)
    database_dict = check_completeness.get_database_dict(engine)
    is_complete, message = check_completeness.check_if_equal(elements_dict, database_dict)

    if is_complete:
        logger.info("All elements are present !")
    else:
        raise ElementsMissing(message)

    if structure:
        # engine, session = clean_tables.setup_db(db_path)

        logging.info("Starting postprocessing...")
        structure = clean_tables.merge_tables(engine, structure)
        logging.info("Postprocessing completed.")

    # create_links.process_structure(structure, engine)

    save_parent_child_structure(structure, structure_file)


