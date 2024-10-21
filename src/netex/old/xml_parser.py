import xml.etree.ElementTree as ET
import json
import sys
import inspect
from models import Base, session  # Make sure your session is imported here
from datetime import datetime
from sqlalchemy.orm import class_mapper, RelationshipProperty
from tqdm import tqdm


def parse_element(element, parent_object=None, session=None, ns=None):
    """Recursively parses an XML element and maps it to a SQLAlchemy model instance."""
    # Remove namespace from tag
    tag = element.tag
    if '}' in tag:
        tag = tag.split('}', 1)[1]

    # Convert tag to model class name (assuming PascalCase)
    model_class_name = ''.join(word.capitalize() for word in tag.split('_'))

    # Attempt to retrieve the model class
    model_class = getattr(sys.modules['models'], model_class_name, None)
    if model_class is None or not inspect.isclass(model_class):
        # No corresponding model class; skip this element
        return None

    # Get model's columns and relationships
    columns = {column.key for column in class_mapper(model_class).columns}
    relationships = {rel.key: rel for rel in class_mapper(model_class).relationships}

    # Prepare data for the model instance
    data = {}

    # Parse element's attributes
    for attr_name, attr_value in element.attrib.items():
        attr_name = attr_name.split('}', 1)[-1]  # Remove namespace if present
        if attr_name in columns:
            data[attr_name] = attr_value
        else:
            # Store unknown attributes in other_attributes
            data.setdefault('other_attributes', {})[attr_name] = attr_value

    # Parse child elements
    for child in element:
        child_tag = child.tag
        if '}' in child_tag:
            child_tag = child_tag.split('}', 1)[1]

        # Handle child elements that correspond to model fields
        if child_tag in columns:
            if child.text and child.text.strip():
                data[child_tag] = child.text.strip()
            else:
                # Handle nested elements (e.g., complex types)
                nested_data = parse_element(child, parent_object=None, session=session, ns=ns)
                if nested_data:
                    data[child_tag] = nested_data
        elif child_tag in relationships:
            # Handle relationships
            rel = relationships[child_tag]
            if rel.uselist:
                # Many-to-many or one-to-many relationship
                items = []
                for sub_child in child:
                    item = parse_element(sub_child, parent_object=None, session=session, ns=ns)
                    if item:
                        items.append(item)
                data[child_tag] = items
            else:
                # One-to-one relationship
                item = parse_element(child, parent_object=None, session=session, ns=ns)
                if item:
                    data[child_tag] = item
        else:
            # Store unknown child elements in other_attributes
            if child.text and child.text.strip():
                data.setdefault('other_attributes', {})[child_tag] = child.text.strip()
            else:
                # Handle nested unknown elements
                data.setdefault('other_attributes', {})[child_tag] = parse_element(child, parent_object=None, session=session, ns=ns)

    # Convert other_attributes to JSON string if present
    if 'other_attributes' in data:
        data['other_attributes'] = json.dumps(data['other_attributes'])

    # Handle datetime fields
    for key, value in data.items():
        if key in columns:
            column_type = getattr(model_class, key).type
            if isinstance(column_type, DateTime):
                try:
                    data[key] = datetime.fromisoformat(value)
                except ValueError:
                    pass  # Keep the original value if parsing fails

    # Create model instance
    instance = model_class(**data)

    # Add instance to session
    if session:
        session.add(instance)
        session.flush()  # To assign IDs

    # Set relationship to parent object if applicable
    if parent_object:
        parent_class = type(parent_object)
        for rel_name, rel in class_mapper(parent_class).relationships.items():
            if rel.mapper.class_ == model_class:
                if rel.uselist:
                    getattr(parent_object, rel_name).append(instance)
                else:
                    setattr(parent_object, rel_name, instance)
                break

    return instance


def populate_database(xml_file, session, test_mode=False):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        ns = {'netex': 'http://www.netex.org.uk/netex'}

        print(f"Processing file: {xml_file}")

        # Start parsing from the root element
        with tqdm(total=1, desc="Parsing XML", leave=True) as pbar:
            parse_element(root, session=session, ns=ns)
            pbar.update(1)

        session.commit()
        print("All data parsed and committed to the database.")

    except Exception as e:
        print(f"Error processing file {xml_file}: {e}")
        session.rollback()
