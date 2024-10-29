import xml.etree.ElementTree as ET
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
import logging
import os


def get_element_dict(file_dir):
    names_dict = {}

    def get_all_elements_names(elem, names_dict):
        # Add the current element's tag to the set
        elem_tag = elem.tag.split('}')[-1]
        if elem_tag not in names_dict.keys():
            names_dict[elem_tag] = 0
        names_dict[elem_tag] += 1
        # Recursively check the element's children
        for child in elem:
            get_all_elements_names(child, names_dict)

    for filename in os.listdir(file_dir):
        tree = ET.parse(os.path.join(file_dir, filename))
        root = tree.getroot()
        get_all_elements_names(root, names_dict)

    names_dict = {"_" + key.lower():value for key, value in names_dict.items()}
    return names_dict


def get_database_dict(engine):
    # Create a connection to the SQLite database
    Session = sessionmaker(bind=engine)
    session = Session()

    # Get all table names using SQLAlchemy's inspector
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # Create a dictionary to store table names and row counts
    table_row_counts = {}

    # For each table, count the number of rows
    for table in tables:
        row_count = session.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar()
        table_row_counts[table] = row_count

    # Close the session
    session.close()

    return table_row_counts

def check_if_equal(elements_dict, database_dict):
    # First, check if both dictionaries have the same keys
    if elements_dict.keys() != database_dict.keys():
        return False, "Keys are not equal"

    # Then, check if the values for each key are equal
    for key in elements_dict:
        if elements_dict[key] != database_dict[key]:
            return False, f"Values are not equal for key {key}. There are {elements_dict[key]} elements for dict1 and {database_dict[key]} for dict2"

    return True, "Dataset is complete."

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    xml_directory = "/home/julien/Documents/pythonProjects/data/test_xmls"
    db_path = "/home/julien/Documents/pythonProjects/data/formated.db"

    elements_dict = get_element_dict(xml_directory)
    database_dict = get_database_dict(db_path)
    print(check_if_equal(elements_dict, database_dict)[1])
