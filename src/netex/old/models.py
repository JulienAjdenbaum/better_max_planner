from sqlalchemy import create_engine, Column, Integer, String, Text, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import json

Base = declarative_base()


class CompositeFrame(Base):
    __tablename__ = 'composite_frame'
    train_numbers = relationship("TrainNumber", back_populates="composite_frame")
    journey_part_couples = relationship("JourneyPartCouple", back_populates="composite_frame")
    coupled_journeys = relationship("CoupledJourney", back_populates="composite_frame")
    types_of_service = relationship("TypeOfService", back_populates="composite_frame")
    uic_operating_periods = relationship("UicOperatingPeriod", back_populates="composite_frame")
    day_type_assignments = relationship("DayTypeAssignment", back_populates="composite_frame")
    service_journeys = relationship("ServiceJourney", back_populates="composite_frame")
    day_types = relationship("DayType", back_populates="composite_frame")
    service_journey_patterns = relationship("ServiceJourneyPattern", back_populates="composite_frame")
    passenger_stop_assignments = relationship("PassengerStopAssignment", back_populates="composite_frame")
    connections = relationship("Connection", back_populates="composite_frame")
    default_connections = relationship("DefaultConnection", back_populates="composite_frame")
    scheduled_stop_points = relationship("ScheduledStopPoint", back_populates="composite_frame")
    route_points = relationship("RoutePoint", back_populates="composite_frame")
    route_links = relationship("RouteLink", back_populates="composite_frame")
    lines = relationship("Line", back_populates="composite_frame")
    destination_displays = relationship("DestinationDisplay", back_populates="composite_frame")
    networks = relationship("Network", back_populates="composite_frame")
    stop_places = relationship("StopPlace", back_populates="composite_frame")
    topographic_places = relationship("TopographicPlace", back_populates="composite_frame")
    journey_parts = relationship("JourneyPart", back_populates="composite_frame")
    id = Column(Integer, primary_key=True)
    frame_id = Column(String(255))
    version = Column(String(255))
    publication_delivery_id = Column(Integer, ForeignKey('publication_delivery.id'))
    other_attributes = Column(Text)

    publication_delivery = relationship("PublicationDelivery", back_populates="composite_frames")
    valid_between = relationship("ValidBetween", back_populates="composite_frame")
    frame_defaults = relationship("FrameDefaults", back_populates="composite_frame")
    service_journeys = relationship("ServiceJourney", back_populates="composite_frame")
    routes = relationship("Route", back_populates="composite_frame")


class PublicationDelivery(Base):
    __tablename__ = 'publication_delivery'
    id = Column(Integer, primary_key=True)
    version = Column(String(255))
    schema_location = Column(Text)
    other_attributes = Column(Text)  # Store any other attributes as a JSON string

    composite_frames = relationship("CompositeFrame", back_populates="publication_delivery")
    publication_timestamps = relationship("PublicationTimestamp", back_populates="publication_delivery")
    participant_refs = relationship("ParticipantRef", back_populates="publication_delivery")
    descriptions = relationship("Description", back_populates="publication_delivery")


class PublicationTimestamp(Base):
    __tablename__ = 'publication_timestamp'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    publication_delivery_id = Column(Integer, ForeignKey('publication_delivery.id'))
    other_attributes = Column(Text)

    publication_delivery = relationship("PublicationDelivery", back_populates="publication_timestamps")


class ParticipantRef(Base):
    __tablename__ = 'participant_ref'
    id = Column(Integer, primary_key=True)
    ref = Column(String(255))
    publication_delivery_id = Column(Integer, ForeignKey('publication_delivery.id'))
    other_attributes = Column(Text)

    publication_delivery = relationship("PublicationDelivery", back_populates="participant_refs")


class Description(Base):
    __tablename__ = 'description'
    id = Column(Integer, primary_key=True)
    lang = Column(String(255))
    content = Column(Text)
    publication_delivery_id = Column(Integer, ForeignKey('publication_delivery.id'))
    other_attributes = Column(Text)

    publication_delivery = relationship("PublicationDelivery", back_populates="descriptions")


class ValidBetween(Base):
    __tablename__ = 'valid_between'
    id = Column(Integer, primary_key=True)
    from_date = Column(String(255))
    to_date = Column(String(255))
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))
    other_attributes = Column(Text)

    composite_frame = relationship("CompositeFrame", back_populates="valid_between")


class FrameDefaults(Base):
    __tablename__ = 'frame_defaults'
    id = Column(Integer, primary_key=True)
    default_locale = Column(String(255))
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))
    other_attributes = Column(Text)

    composite_frame = relationship("CompositeFrame", back_populates="frame_defaults")


class Route(Base):
    __tablename__ = 'route'
    id = Column(Integer, primary_key=True)
    route_id = Column(String(255))
    version = Column(String(255))
    distance = Column(Integer)
    line_ref = Column(String(255))
    direction_type = Column(String(255))
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))
    other_attributes = Column(Text)

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
    other_attributes = Column(Text)

    route = relationship("Route", back_populates="points_in_sequence")


class JourneyPart(Base):
    __tablename__ = 'journey_part'
    id = Column(Integer, primary_key=True)
    journey_part_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    parent_journey_ref = Column(String(255))
    main_part_ref = Column(String(255))
    train_number_ref = Column(String(255))
    from_stop_point_ref = Column(String(255))
    to_stop_point_ref = Column(String(255))
    start_time = Column(String(50))
    end_time = Column(String(50))
    end_time_day_offset = Column(Integer)
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))  # Add this line
    other_attributes = Column(Text)

    composite_frame = relationship("CompositeFrame", back_populates="journey_parts")


class TopographicPlace(Base):
    __tablename__ = 'topographic_place'
    id = Column(Integer, primary_key=True)
    topographic_place_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    private_code = Column(String(255))
    name = Column(String(255))
    lang = Column(String(10))
    topographic_place_type = Column(String(255))
    country_ref = Column(String(10))
    parent_topographic_place_ref = Column(String(255))
    other_attributes = Column(Text)
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="topographic_places")


class StopPlace(Base):
    __tablename__ = 'stop_place'
    id = Column(Integer, primary_key=True)
    stop_place_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    created = Column(DateTime)
    changed = Column(DateTime)
    modification = Column(String(50))
    valid_from_date = Column(DateTime)
    valid_to_date = Column(DateTime)
    name = Column(String(255))
    short_name = Column(String(255))
    private_code = Column(String(255))
    longitude = Column(Float)
    latitude = Column(Float)
    place_type_ref = Column(String(255))
    country_ref = Column(String(10))
    house_number = Column(String(50))
    street = Column(String(255))
    town = Column(String(255))
    post_code = Column(String(50))
    postal_region = Column(String(255))
    topographic_place_ref = Column(String(255))
    time_zone_offset = Column(String(10))
    time_zone = Column(String(50))
    summer_time_zone_offset = Column(String(10))
    default_language = Column(String(10))
    transport_mode = Column(String(50))
    other_transport_modes = Column(String(255))
    stop_place_type = Column(String(50))
    other_attributes = Column(Text)
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="stop_places")
    alternative_names = relationship("AlternativeName", back_populates="stop_place")


class AlternativeName(Base):
    __tablename__ = 'alternative_name'
    id = Column(Integer, primary_key=True)
    lang = Column(String(10))
    name_type = Column(String(50))
    type_of_name = Column(String(255))
    name = Column(String(255))
    stop_place_id = Column(Integer, ForeignKey('stop_place.id'))

    stop_place = relationship("StopPlace", back_populates="alternative_names")


class Network(Base):
    __tablename__ = 'network'
    id = Column(Integer, primary_key=True)
    network_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    name = Column(String(255))
    other_attributes = Column(Text)
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="networks")
    groups_of_lines = relationship("GroupOfLines", back_populates="network")


class GroupOfLines(Base):
    __tablename__ = 'group_of_lines'
    id = Column(Integer, primary_key=True)
    group_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    name = Column(String(255))
    network_id = Column(Integer, ForeignKey('network.id'))
    other_attributes = Column(Text)

    network = relationship("Network", back_populates="groups_of_lines")
    line_refs = relationship("LineRef", back_populates="group_of_lines")


class LineRef(Base):
    __tablename__ = 'line_ref'
    id = Column(Integer, primary_key=True)
    ref = Column(String(255))
    group_of_lines_id = Column(Integer, ForeignKey('group_of_lines.id'))

    group_of_lines = relationship("GroupOfLines", back_populates="line_refs")


class RoutePoint(Base):
    __tablename__ = 'route_point'
    id = Column(Integer, primary_key=True)
    route_point_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    longitude = Column(Float)
    latitude = Column(Float)
    other_attributes = Column(Text)
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="route_points")


class RouteLink(Base):
    __tablename__ = 'route_link'
    id = Column(Integer, primary_key=True)
    route_link_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    distance = Column(Float)
    from_point_ref = Column(String(255))
    to_point_ref = Column(String(255))
    other_attributes = Column(Text)
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="route_links")


class Line(Base):
    __tablename__ = 'line'
    id = Column(Integer, primary_key=True)
    line_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    responsibility_set_ref = Column(String(255))
    name = Column(String(255))
    description = Column(Text)
    transport_mode = Column(String(50))
    transport_submode = Column(String(50))
    public_code = Column(String(255))
    operator_ref = Column(String(255))
    other_attributes = Column(Text)
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="lines")
    route_refs = relationship("RouteRef", back_populates="line")


class RouteRef(Base):
    __tablename__ = 'route_ref'
    id = Column(Integer, primary_key=True)
    ref = Column(String(255))
    line_id = Column(Integer, ForeignKey('line.id'))

    line = relationship("Line", back_populates="route_refs")


class DestinationDisplay(Base):
    __tablename__ = 'destination_display'
    id = Column(Integer, primary_key=True)
    destination_display_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    side_text = Column(String(255))
    front_text = Column(String(255))
    other_attributes = Column(Text)
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="destination_displays")


class ScheduledStopPoint(Base):
    __tablename__ = 'scheduled_stop_point'
    id = Column(Integer, primary_key=True)
    scheduled_stop_point_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    name = Column(String(255))
    lang = Column(String(10))
    longitude = Column(Float)
    latitude = Column(Float)
    public_code = Column(String(255))
    other_attributes = Column(Text)
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="scheduled_stop_points")


class Connection(Base):
    __tablename__ = 'connection'
    id = Column(Integer, primary_key=True)
    connection_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    name = Column(String(255))
    default_duration = Column(String(50))  # Duration in ISO 8601 format
    both_ways = Column(Boolean)
    from_scheduled_stop_point_ref = Column(String(255))
    to_scheduled_stop_point_ref = Column(String(255))
    other_attributes = Column(Text)
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="connections")


class DefaultConnection(Base):
    __tablename__ = 'default_connection'
    id = Column(Integer, primary_key=True)
    default_connection_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    default_duration = Column(String(50))  # Duration in ISO 8601 format
    both_ways = Column(Boolean)
    from_transport_mode = Column(String(50))
    to_transport_mode = Column(String(50))
    other_attributes = Column(Text)
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="default_connections")


class PassengerStopAssignment(Base):
    __tablename__ = 'passenger_stop_assignment'
    id = Column(Integer, primary_key=True)
    assignment_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    order = Column(Integer)
    scheduled_stop_point_ref = Column(String(255))
    stop_place_ref = Column(String(255))
    other_attributes = Column(Text)
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="passenger_stop_assignments")


class ServiceJourneyPattern(Base):
    __tablename__ = 'service_journey_pattern'
    id = Column(Integer, primary_key=True)
    journey_pattern_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    distance = Column(Float)
    destination_display_ref = Column(String(255))
    service_journey_pattern_type = Column(String(50))
    other_attributes = Column(Text)
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="service_journey_patterns")
    stop_points_in_journey_pattern = relationship("StopPointInJourneyPattern", back_populates="service_journey_pattern")


class StopPointInJourneyPattern(Base):
    __tablename__ = 'stop_point_in_journey_pattern'
    id = Column(Integer, primary_key=True)
    stop_point_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    order = Column(Integer)
    scheduled_stop_point_ref = Column(String(255))
    journey_pattern_id = Column(Integer, ForeignKey('service_journey_pattern.id'))

    service_journey_pattern = relationship("ServiceJourneyPattern", back_populates="stop_points_in_journey_pattern")


class DayType(Base):
    __tablename__ = 'day_type'
    id = Column(Integer, primary_key=True)
    day_type_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    other_attributes = Column(Text)
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="day_types")


class UicOperatingPeriod(Base):
    __tablename__ = 'uic_operating_period'
    id = Column(Integer, primary_key=True)
    operating_period_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    from_date = Column(DateTime)
    to_date = Column(DateTime)
    valid_day_bits = Column(String(255))
    other_attributes = Column(Text)
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="uic_operating_periods")


class DayTypeAssignment(Base):
    __tablename__ = 'day_type_assignment'
    id = Column(Integer, primary_key=True)
    assignment_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    order = Column(Integer)
    uic_operating_period_ref = Column(String(255))
    day_type_ref = Column(String(255))
    other_attributes = Column(Text)
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="day_type_assignments")


class ServiceJourney(Base):
    __tablename__ = 'service_journey'
    id = Column(Integer, primary_key=True)
    service_journey_id = Column(String(255), unique=True, nullable=False)
    responsibility_set_ref = Column(String(255))
    data_source_ref = Column(String(255))
    changed = Column(DateTime)
    version = Column(String(50))
    status = Column(String(50))
    valid_from_date = Column(DateTime)
    valid_to_date = Column(DateTime)
    branding_ref = Column(String(255))
    distance = Column(Float)
    transport_mode = Column(String(50))
    transport_submode = Column(String(50))
    service_alteration = Column(String(50))
    departure_time = Column(String(50))
    journey_pattern_ref = Column(String(255))
    operator_ref = Column(String(255))
    line_ref = Column(String(255))
    other_attributes = Column(Text)
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))

    composite_frame = relationship("CompositeFrame", back_populates="service_journeys")
    train_numbers = relationship("TrainNumberRef", back_populates="service_journey")
    passing_times = relationship("TimetabledPassingTime", back_populates="service_journey")
    facilities = relationship("ServiceFacilitySet", back_populates="service_journey")
    day_types = relationship("DayTypeRef", back_populates="service_journey")


class TrainNumberRef(Base):
    __tablename__ = 'train_number_ref'
    id = Column(Integer, primary_key=True)
    ref = Column(String(255))
    version = Column(String(50))
    service_journey_id = Column(Integer, ForeignKey('service_journey.id'))

    service_journey = relationship("ServiceJourney", back_populates="train_numbers")


class ServiceFacilitySet(Base):
    __tablename__ = 'service_facility_set'
    id = Column(Integer, primary_key=True)
    facility_set_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    fare_classes = Column(String(255))
    accommodation_facility_list = Column(String(255))
    luggage_carriage_facility_list = Column(String(255))
    service_reservation_facility_list = Column(String(255))
    other_attributes = Column(Text)
    service_journey_id = Column(Integer, ForeignKey('service_journey.id'))

    service_journey = relationship("ServiceJourney", back_populates="facilities")


class DayTypeRef(Base):
    __tablename__ = 'day_type_ref'
    id = Column(Integer, primary_key=True)
    ref = Column(String(255))
    service_journey_id = Column(Integer, ForeignKey('service_journey.id'))

    service_journey = relationship("ServiceJourney", back_populates="day_types")

class TimetabledPassingTime(Base):
    __tablename__ = 'timetabled_passing_time'
    id = Column(Integer, primary_key=True)
    point_in_journey_pattern_ref = Column(String(255))
    arrival_time = Column(String(50))
    departure_time = Column(String(50))
    service_journey_id = Column(Integer, ForeignKey('service_journey.id'))

    service_journey = relationship("ServiceJourney", back_populates="passing_times")

class TrainNumber(Base):
    __tablename__ = 'train_number'
    id = Column(Integer, primary_key=True)
    train_number_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    responsibility_set_ref = Column(String(255))
    for_advertisement = Column(String(255))
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))
    other_attributes = Column(Text)

    composite_frame = relationship("CompositeFrame", back_populates="train_numbers")

class JourneyPartCouple(Base):
    __tablename__ = 'journey_part_couple'
    id = Column(Integer, primary_key=True)
    journey_part_couple_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    order = Column(Integer)
    start_time = Column(String(50))
    start_time_day_offset = Column(Integer)
    end_time = Column(String(50))
    end_time_day_offset = Column(Integer)
    from_stop_point_ref = Column(String(255))
    to_stop_point_ref = Column(String(255))
    main_part_ref = Column(String(255))
    train_number_ref = Column(String(255))
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))
    other_attributes = Column(Text)

    composite_frame = relationship("CompositeFrame", back_populates="journey_part_couples")
    journey_part_refs = relationship("JourneyPartRef", back_populates="journey_part_couple")

class JourneyPartRef(Base):
    __tablename__ = 'journey_part_ref'
    id = Column(Integer, primary_key=True)
    ref = Column(String(255))
    version = Column(String(50))
    journey_part_couple_id = Column(Integer, ForeignKey('journey_part_couple.id'))

    journey_part_couple = relationship("JourneyPartCouple", back_populates="journey_part_refs")

class CoupledJourney(Base):
    __tablename__ = 'coupled_journey'
    id = Column(Integer, primary_key=True)
    coupled_journey_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))
    other_attributes = Column(Text)

    composite_frame = relationship("CompositeFrame", back_populates="coupled_journeys")
    vehicle_journey_refs = relationship("VehicleJourneyRef", back_populates="coupled_journey")

class VehicleJourneyRef(Base):
    __tablename__ = 'vehicle_journey_ref'
    id = Column(Integer, primary_key=True)
    ref = Column(String(255))
    version = Column(String(50))
    coupled_journey_id = Column(Integer, ForeignKey('coupled_journey.id'))

    coupled_journey = relationship("CoupledJourney", back_populates="vehicle_journey_refs")

class TypeOfService(Base):
    __tablename__ = 'type_of_service'
    id = Column(Integer, primary_key=True)
    type_of_service_id = Column(String(255), unique=True, nullable=False)
    version = Column(String(50))
    name = Column(String(255))
    name_lang = Column(String(10))
    short_name = Column(String(255))
    short_name_lang = Column(String(10))
    private_code = Column(String(255))
    composite_frame_id = Column(Integer, ForeignKey('composite_frame.id'))
    other_attributes = Column(Text)

    composite_frame = relationship("CompositeFrame", back_populates="types_of_service")


