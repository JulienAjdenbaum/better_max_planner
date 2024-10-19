from sqlalchemy import create_engine, Column, Integer, String, Text, Float, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import xml.etree.ElementTree as ET
import os

# Create a base class for the SQLAlchemy models
Base = declarative_base()

# Define the database schema based on the XML structure

class PublicationDelivery(Base):
    __tablename__ = 'publication_delivery'
    id = Column(Integer, primary_key=True)
    version = Column(String(255))
    schema_location = Column(Text)

    composite_frames = relationship("CompositeFrame", back_populates="publication_delivery")
    publication_timestamps = relationship("PublicationTimestamp", back_populates="publication_delivery")
    participant_refs = relationship("ParticipantRef", back_populates="publication_delivery")
    descriptions = relationship("Description", back_populates="publication_delivery")

class PublicationTimestamp(Base):
    __tablename__ = 'publication_timestamp'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    publication_delivery_id = Column(Integer, ForeignKey('publication_delivery.id'))

    publication_delivery = relationship("PublicationDelivery", back_populates="publication_timestamps")

class ParticipantRef(Base):
    __tablename__ = 'participant_ref'
    id = Column(Integer, primary_key=True)
    ref = Column(String(255))
    publication_delivery_id = Column(Integer, ForeignKey('publication_delivery.id'))

    publication_delivery = relationship("PublicationDelivery", back_populates="participant_refs")

class Description(Base):
    __tablename__ = 'description'
    id = Column(Integer, primary_key=True)
    lang = Column(String(255))
    content = Column(Text)
    publication_delivery_id = Column(Integer, ForeignKey('publication_delivery.id'))

    publication_delivery = relationship("PublicationDelivery", back_populates="descriptions")

class CompositeFrame(Base):
    __tablename__ = 'composite_frame'
    id = Column(Integer, primary_key=True)
    frame_id = Column(String(255))
    version = Column(String(255))
    publication_delivery_id = Column(Integer, ForeignKey('publication_delivery.id'))

    publication_delivery = relationship("PublicationDelivery", back_populates="composite_frames")
    valid_between = relationship("ValidBetween", back_populates="composite_frame")
    frame_defaults = relationship("FrameDefaults", back_populates="composite_frame")
    service_journeys = relationship("ServiceJourney", back_populates="composite_frame")

class ValidBetween(Base):
    __tablename__ = 'valid_between'
    id = Column(Integer, primary_key=True)
    from_date = Column(String(255))
    to_date = Column(String(255))
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="valid_between")

class FrameDefaults(Base):
    __tablename__ = 'frame_defaults'
    id = Column(Integer, primary_key=True)
    default_locale = Column(String(255))
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="frame_defaults")

class ServiceJourney(Base):
    __tablename__ = 'service_journey'
    id = Column(Integer, primary_key=True)
    journey_id = Column(String(255))
    departure_time = Column(String(255))
    destination_ref = Column(String(255))
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="service_journeys")

# Connect to SQLite database
engine = create_engine('sqlite:///netex.db')
Session = sessionmaker(bind=engine)

# Function to create the database schema
def create_db():
    Base.metadata.create_all(engine)
    print("Database schema created.")

# Function to drop the database schema
def reset_db():
    Base.metadata.drop_all(engine)
    create_db()
    print("Database reset.")

# Helper function for safe element lookup and debugging
def find_element_debug(root, path, ns):
    elem = root.find(path, ns)
    if elem is not None and elem.text is not None:
        print(f"Found element: {path} -> {elem.text.strip()}")
    elif elem is not None:
        print(f"Found element: {path} -> No Text")
    else:
        print(f"Element not found: {path}")
    return elem

# Function to safely extract text from an element
def get_element_text(element, path, ns):
    child = element.find(path, ns)
    if child is not None and child.text:
        return child.text.strip()
    return None

# Function to populate the database with data from an XML file
def populate_database(xml_file, session):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        ns = {'netex': 'http://www.netex.org.uk/netex'}

        print(f"Processing file: {xml_file}")
        print(f"Root tag: {root.tag}, attributes: {root.attrib}")

        # Extract and insert PublicationDelivery
        publication_delivery = PublicationDelivery(
            version=root.attrib.get('version'),
            schema_location=root.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation')
        )
        session.add(publication_delivery)
        session.commit()
        print("Inserted PublicationDelivery")

        # Insert PublicationTimestamp
        for pub_timestamp_elem in root.findall('.//netex:PublicationTimestamp', ns):
            if pub_timestamp_elem is not None and pub_timestamp_elem.text:
                try:
                    timestamp = datetime.fromisoformat(pub_timestamp_elem.text.strip())
                    pub_timestamp = PublicationTimestamp(
                        timestamp=timestamp,
                        publication_delivery_id=publication_delivery.id
                    )
                    session.add(pub_timestamp)
                except Exception as e:
                    print(f"Error parsing timestamp {pub_timestamp_elem.text}: {e}")
            else:
                print("PublicationTimestamp found but is empty or missing text")

        # Insert ParticipantRef
        for participant_ref_elem in root.findall('.//netex:ParticipantRef', ns):
            if participant_ref_elem is not None and participant_ref_elem.text:
                participant_ref = ParticipantRef(
                    ref=participant_ref_elem.text.strip(),
                    publication_delivery_id=publication_delivery.id
                )
                session.add(participant_ref)
            else:
                print("ParticipantRef found but is empty or missing text")

        # Insert Description
        for description_elem in root.findall('.//netex:Description', ns):
            if description_elem is not None and description_elem.text:
                description = Description(
                    lang=description_elem.attrib.get('lang'),
                    content=description_elem.text.strip(),
                    publication_delivery_id=publication_delivery.id
                )
                session.add(description)
            else:
                print("Description found but is empty or missing text")

        # Insert CompositeFrame and nested elements
        for composite_frame_elem in root.findall('.//netex:CompositeFrame', ns):
            if composite_frame_elem is not None:
                composite_frame = CompositeFrame(
                    frame_id=composite_frame_elem.attrib.get('id'),
                    version=composite_frame_elem.attrib.get('version'),
                    publication_delivery_id=publication_delivery.id
                )
                session.add(composite_frame)
                session.commit()
                print("Inserted CompositeFrame")

                # Insert ValidBetween
                for valid_between_elem in composite_frame_elem.findall('.//netex:ValidBetween', ns):
                    if valid_between_elem is not None:
                        valid_between = ValidBetween(
                            from_date=get_element_text(valid_between_elem, 'netex:FromDate', ns),
                            to_date=get_element_text(valid_between_elem, 'netex:ToDate', ns),
                            composite_frame_id=composite_frame.id
                        )
                        session.add(valid_between)
                        print("Inserted ValidBetween")

                # Insert FrameDefaults
                frame_defaults_elem = composite_frame_elem.find('.//netex:FrameDefaults', ns)
                if frame_defaults_elem is not None:
                    frame_defaults = FrameDefaults(
                        default_locale=get_element_text(frame_defaults_elem, 'netex:DefaultLocale/netex:DefaultLanguage', ns),
                        composite_frame_id=composite_frame.id
                    )
                    session.add(frame_defaults)
                    print("Inserted FrameDefaults")

                # Insert ServiceJourney
                for service_journey_elem in composite_frame_elem.findall('.//netex:ServiceJourney', ns):
                    journey_id = service_journey_elem.attrib.get('id')
                    departure_time = get_element_text(service_journey_elem, 'netex:DepartureTime', ns)
                    destination_ref = get_element_text(service_journey_elem, 'netex:DestinationRef', ns)

                    if journey_id is not None:
                        service_journey = ServiceJourney(
                            journey_id=journey_id,
                            departure_time=departure_time,
                            destination_ref=destination_ref,
                            composite_frame_id=composite_frame.id
                        )
                        session.add(service_journey)
                        print(f"Inserted ServiceJourney with id {journey_id}")

        # Commit after all inserts
        session.commit()
        print(f"Data from {xml_file} inserted into the database.\n")

    except Exception as e:
        print(f"Error processing file {xml_file}: {e}")

# Function to process all XML files in the directory
def process_files(directory, reset=False):
    # Create a new session
    session = Session()

    if reset:
        reset_db()

    # Iterate over all XML files in the directory
    for filename in os.listdir(directory):
        if filename.endswith(".xml"):
            file_path = os.path.join(directory, filename)
            print(f"Processing file: {file_path}")
            populate_database(file_path, session)

    print("All files processed.")

# Main function to control the process
def main():
    directory = 'data/netex_xml'  # Update this to point to your directory
    option = 'reset'

    if option == 'reset':
        process_files(directory, reset=True)
    elif option == 'append':
        process_files(directory, reset=False)
    else:
        print("Invalid option. Please choose 'reset' or 'append'.")

if __name__ == "__main__":
    main()
