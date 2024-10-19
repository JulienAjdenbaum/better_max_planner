from sqlalchemy import create_engine, Column, Integer, String, Text, Float, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

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

# Update CompositeFrame in models.py to add the routes relationship

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
    routes = relationship("Route", back_populates="composite_frame")


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

class Route(Base):
    __tablename__ = 'route'
    id = Column(Integer, primary_key=True)
    route_id = Column(String(255))
    version = Column(String(255))
    distance = Column(Integer)
    line_ref = Column(String(255))
    direction_type = Column(String(255))
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="routes")
    points_in_sequence = relationship("PointOnRoute", back_populates="route")

class PointOnRoute(Base):
    __tablename__ = 'point_on_route'
    id = Column(Integer, primary_key=True)
    point_on_route_id = Column(String(255))
    version = Column(String(255))
    order = Column(Integer)
    route_id = Column(Integer, ForeignKey('route.id'))
    route_point_ref = Column(String(255))

    route = relationship("Route", back_populates="points_in_sequence")
