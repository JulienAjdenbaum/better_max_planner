import xml.etree.ElementTree as ET
import json
from models import *
from datetime import datetime
from tqdm import tqdm


def parse_element_attributes(element):
    """Helper function to parse all attributes from an XML element."""
    attributes = {}
    for key, value in element.attrib.items():
        attributes[key] = value
    return attributes


def get_element_text(element, tag_name, ns):
    """Helper function to extract text from an element by tag."""
    child = element.find(tag_name, ns)
    if child is not None and child.text:
        return child.text.strip()
    return None


def parse_generic_element(element, field_mapping, ns):
    """Parses fields from an element based on a mapping and stores the rest in other_attributes."""
    parsed_data = {}
    other_attributes = parse_element_attributes(element)

    for xml_field, model_field in field_mapping.items():
        # Check if xml_field is an attribute of the main element
        if xml_field in other_attributes:
            parsed_data[model_field] = other_attributes.pop(xml_field, None)
        else:
            # Handle nested elements
            child = element.find(f'netex:{xml_field}', ns)
            if child is not None:
                # Check for 'ref' attribute
                ref = child.attrib.get('ref')
                if ref:
                    parsed_data[model_field] = ref
                else:
                    # Check for text content
                    if child.text:
                        parsed_data[model_field] = child.text.strip()
                    else:
                        parsed_data[model_field] = None
            else:
                parsed_data[model_field] = None

    parsed_data["other_attributes"] = json.dumps(other_attributes) if other_attributes else None
    return parsed_data





def populate_generic_model(session, model_class, element, field_mapping, ns, **kwargs):
    """Populates a database model instance using the XML data."""
    parsed_data = parse_generic_element(element, field_mapping, ns)
    instance_data = {**parsed_data, **kwargs}
    instance = model_class(**instance_data)
    session.add(instance)
    return instance


def populate_publication_delivery(root, session, ns):
    field_mapping = {'version': 'version',
                     '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation': 'schema_location'}
    publication_delivery = populate_generic_model(session, PublicationDelivery, root, field_mapping, ns)
    session.commit()
    print("Inserted PublicationDelivery")
    return publication_delivery


def populate_composite_frame(publication_delivery, composite_frame_elem, session, ns):
    field_mapping = {'id': 'frame_id', 'version': 'version'}
    composite_frame = populate_generic_model(session, CompositeFrame, composite_frame_elem, field_mapping, ns,
                                             publication_delivery_id=publication_delivery.id)
    session.commit()
    print(f"Inserted CompositeFrame with ID: {composite_frame.frame_id}")

    populate_journey_part(composite_frame, composite_frame_elem, session, ns)
    populate_routes(composite_frame, composite_frame_elem, session, ns)
    populate_topographic_places(composite_frame, composite_frame_elem, session, ns)
    populate_stop_places(composite_frame, composite_frame_elem, session, ns)
    populate_networks(composite_frame, composite_frame_elem, session, ns)
    populate_route_points(composite_frame, composite_frame_elem, session, ns)
    populate_route_links(composite_frame, composite_frame_elem, session, ns)
    populate_lines(composite_frame, composite_frame_elem, session, ns)
    populate_destination_displays(composite_frame, composite_frame_elem, session, ns)
    populate_scheduled_stop_points(composite_frame, composite_frame_elem, session, ns)
    populate_connections(composite_frame, composite_frame_elem, session, ns)
    populate_default_connections(composite_frame, composite_frame_elem, session, ns)
    populate_passenger_stop_assignments(composite_frame, composite_frame_elem, session, ns)
    populate_service_journey_patterns(composite_frame, composite_frame_elem, session, ns)
    populate_day_types(composite_frame, composite_frame_elem, session, ns)
    populate_uic_operating_periods(composite_frame, composite_frame_elem, session, ns)
    populate_day_type_assignments(composite_frame, composite_frame_elem, session, ns)
    populate_service_journeys(composite_frame, composite_frame_elem, session, ns)
    populate_train_numbers(composite_frame, composite_frame_elem, session, ns)
    populate_journey_part_couples(composite_frame, composite_frame_elem, session, ns)
    populate_coupled_journeys(composite_frame, composite_frame_elem, session, ns)
    populate_types_of_service(composite_frame, composite_frame_elem, session, ns)



def populate_journey_part(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    # Correct XPath to locate JourneyPart elements
    journey_parts = composite_frame_elem.findall('.//netex:GeneralFrame/netex:members/netex:JourneyPart', ns)
    print(f"Found {len(journey_parts)} JourneyPart elements")

    if len(journey_parts) == 0:
        print("Warning: No JourneyPart elements found. Please check the XML structure or namespace definitions.")
        return

    # Limit the number of journey parts processed in test mode
    if test_mode:
        journey_parts = journey_parts[:100]

    # Mapping XML fields to model fields
    field_mapping = {
        'id': 'journey_part_id',
        'version': 'version',
        'ParentJourneyRef': 'parent_journey_ref',
        'MainPartRef': 'main_part_ref',
        'TrainNumberRef': 'train_number_ref',
        'FromStopPointRef': 'from_stop_point_ref',
        'ToStopPointRef': 'to_stop_point_ref',
        'StartTime': 'start_time',
        'EndTime': 'end_time',
        'EndTimeDayOffset': 'end_time_day_offset'
    }

    # Process each JourneyPart element
    for journey_part_elem in journey_parts:
        # Debug: Print out the journey_part element's XML
        print("JourneyPart element:", ET.tostring(journey_part_elem, encoding='unicode'))

        # Extract and populate JourneyPart using a generic model function
        try:
            journey_part = populate_generic_model(session, JourneyPart, journey_part_elem, field_mapping, ns, composite_frame_id=composite_frame.id)
            if not journey_part:
            #     print(f"Inserted JourneyPart with ID: {journey_part.journey_part_id}")
            # else:
                print(f"Failed to create JourneyPart for element: {ET.tostring(journey_part_elem, encoding='unicode')}")
        except TypeError as e:
            print(f"Error inserting JourneyPart: {e}")
            continue

    # Commit session to save JourneyPart elements
    session.commit()




def populate_routes(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    # Correct XPath to locate Route elements
    routes = composite_frame_elem.findall('.//netex:ServiceFrame/netex:routes/netex:Route', ns)
    print(f"Found {len(routes)} Route elements in CompositeFrame {composite_frame.frame_id}")

    # Limit the number of routes processed in test mode
    if test_mode:
        routes = routes[:100]

    # Add a single progress bar for all routes under this composite frame
    with tqdm(total=len(routes), desc="Processing Routes", leave=True) as pbar_routes:
        for route_elem in routes:
            try:
                # Extract attributes
                route_id = route_elem.attrib.get('id')
                version = route_elem.attrib.get('version')
                distance = get_element_text(route_elem, 'netex:Distance', ns)
                line_ref_elem = route_elem.find('netex:LineRef', ns)
                line_ref = line_ref_elem.attrib.get('ref') if line_ref_elem is not None else None
                direction_type = get_element_text(route_elem, 'netex:DirectionType', ns)

                # If Route ID is missing, skip this entry
                if route_id is None:
                    print(f"Warning: Route element missing ID. Skipping.")
                    pbar_routes.update(1)
                    continue

                # Create a new Route entry
                route = Route(
                    route_id=route_id,
                    version=version,
                    distance=int(distance) if distance is not None else None,
                    line_ref=line_ref,
                    direction_type=direction_type,
                    composite_frame_id=composite_frame.id
                )
                session.add(route)
                # print(f"Inserted Route with ID: {route_id}")

                # Insert PointOnRoute elements
                points = route_elem.findall('.//netex:PointOnRoute', ns)
                # print(f"Found {len(points)} PointOnRoute elements in Route {route_id}")
                for point_elem in points:
                    point_id = point_elem.attrib.get('id')
                    version = point_elem.attrib.get('version')
                    order = point_elem.attrib.get('order')
                    route_point_ref_elem = point_elem.find('netex:RoutePointRef', ns)
                    route_point_ref = route_point_ref_elem.attrib.get(
                        'ref') if route_point_ref_elem is not None else None

                    if point_id is None:
                        print(f"Warning: PointOnRoute element missing ID. Skipping.")
                        continue

                    point_on_route = PointOnRoute(
                        point_on_route_id=point_id,
                        version=version,
                        order=int(order) if order is not None else None,
                        route_id=route.id,
                        route_point_ref=route_point_ref
                    )
                    session.add(point_on_route)
                    # print(f"Inserted PointOnRoute with ID: {point_id}")

                # Update progress bar for routes
                pbar_routes.update(1)
                session.add(route)
                session.flush()  # Add this line to assign an ID to route.id
            except Exception as e:
                print(f"Error inserting Route or PointOnRoute: {e}")
                session.rollback()

    session.commit()



def populate_database(xml_file, session, test_mode=False):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        ns = {'netex': 'http://www.netex.org.uk/netex'}

        print(f"Processing file: {xml_file}")
        print(f"Root tag: {root.tag}, attributes: {root.attrib}")

        publication_delivery = populate_publication_delivery(root, session, ns)

        composite_frames = root.findall('.//netex:CompositeFrame', ns)
        print(f"Found {len(composite_frames)} CompositeFrame elements")
        for composite_frame_elem in tqdm(composite_frames, desc="Processing CompositeFrames"):
            populate_composite_frame(publication_delivery, composite_frame_elem, session, ns)

    except Exception as e:
        print(f"Error processing file {xml_file}: {e}")

def populate_topographic_places(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    topographic_places = composite_frame_elem.findall('.//netex:SiteFrame/netex:topographicPlaces/netex:TopographicPlace', ns)
    print(f"Found {len(topographic_places)} TopographicPlace elements")

    # Limit the number of topographic places processed in test mode
    if test_mode:
        topographic_places = topographic_places[:100]

    field_mapping = {
        'id': 'topographic_place_id',
        'version': 'version',
        'PrivateCode': 'private_code',
        'TopographicPlaceType': 'topographic_place_type',
        'CountryRef': 'country_ref',
        'ParentTopographicPlaceRef': 'parent_topographic_place_ref'
    }

    for place_elem in topographic_places:
        try:
            # Extract fields using parse_generic_element
            parsed_data = parse_generic_element(place_elem, field_mapping, ns)

            # Handle 'Descriptor/Name' element separately
            descriptor_elem = place_elem.find('netex:Descriptor', ns)
            if descriptor_elem is not None:
                name_elem = descriptor_elem.find('netex:Name', ns)
                if name_elem is not None:
                    parsed_data['name'] = name_elem.text.strip() if name_elem.text else None
                    parsed_data['lang'] = name_elem.attrib.get('lang')
                else:
                    parsed_data['name'] = None
                    parsed_data['lang'] = None
            else:
                parsed_data['name'] = None
                parsed_data['lang'] = None

            # Add composite_frame_id
            parsed_data['composite_frame_id'] = composite_frame.id

            # Create TopographicPlace instance
            topographic_place = TopographicPlace(**parsed_data)
            session.add(topographic_place)
            # print(f"Inserted TopographicPlace with ID: {parsed_data['topographic_place_id']}")

        except Exception as e:
            print(f"Error inserting TopographicPlace: {e}")
            session.rollback()

    session.commit()

def populate_stop_places(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    stop_places = composite_frame_elem.findall('.//netex:SiteFrame/netex:stopPlaces/netex:StopPlace', ns)
    print(f"Found {len(stop_places)} StopPlace elements")

    # Limit the number of stop places processed in test mode
    if test_mode:
        stop_places = stop_places[:100]

    field_mapping = {
        'id': 'stop_place_id',
        'version': 'version',
        'created': 'created',
        'changed': 'changed',
        'modification': 'modification',
        'Name': 'name',
        'ShortName': 'short_name',
        'PrivateCode': 'private_code',
        'TransportMode': 'transport_mode',
        'OtherTransportModes': 'other_transport_modes',
        'StopPlaceType': 'stop_place_type'
    }

    for place_elem in stop_places:
        try:
            # Parse attributes and immediate child elements
            parsed_data = parse_generic_element(place_elem, field_mapping, ns)

            # Convert 'created' and 'changed' to datetime objects
            if parsed_data.get('created'):
                parsed_data['created'] = datetime.fromisoformat(parsed_data['created'])
            if parsed_data.get('changed'):
                parsed_data['changed'] = datetime.fromisoformat(parsed_data['changed'])

            # Handle ValidBetween
            valid_between_elem = place_elem.find('netex:ValidBetween', ns)
            if valid_between_elem is not None:
                from_date = get_element_text(valid_between_elem, 'netex:FromDate', ns)
                to_date = get_element_text(valid_between_elem, 'netex:ToDate', ns)
                parsed_data['valid_from_date'] = datetime.fromisoformat(from_date) if from_date else None
                parsed_data['valid_to_date'] = datetime.fromisoformat(to_date) if to_date else None
            else:
                parsed_data['valid_from_date'] = None
                parsed_data['valid_to_date'] = None

            # Handle Centroid/Location/Longitude and Latitude
            centroid_elem = place_elem.find('netex:Centroid/netex:Location', ns)
            if centroid_elem is not None:
                longitude = get_element_text(centroid_elem, 'netex:Longitude', ns)
                latitude = get_element_text(centroid_elem, 'netex:Latitude', ns)
                parsed_data['longitude'] = float(longitude) if longitude else None
                parsed_data['latitude'] = float(latitude) if latitude else None
            else:
                parsed_data['longitude'] = None
                parsed_data['latitude'] = None

            # Handle placeTypes/TypeOfPlaceRef
            type_of_place_ref_elem = place_elem.find('netex:placeTypes/netex:TypeOfPlaceRef', ns)
            if type_of_place_ref_elem is not None:
                parsed_data['place_type_ref'] = type_of_place_ref_elem.attrib.get('ref')
            else:
                parsed_data['place_type_ref'] = None

            # Handle PostalAddress and its subelements
            postal_address_elem = place_elem.find('netex:PostalAddress', ns)
            if postal_address_elem is not None:
                country_ref = get_element_text(postal_address_elem, 'netex:CountryRef', ns)
                house_number = get_element_text(postal_address_elem, 'netex:HouseNumber', ns)
                street = get_element_text(postal_address_elem, 'netex:Street', ns)
                town = get_element_text(postal_address_elem, 'netex:Town', ns)
                post_code = get_element_text(postal_address_elem, 'netex:PostCode', ns)
                postal_region = get_element_text(postal_address_elem, 'netex:PostalRegion', ns)
                parsed_data.update({
                    'country_ref': country_ref,
                    'house_number': house_number,
                    'street': street,
                    'town': town,
                    'post_code': post_code,
                    'postal_region': postal_region
                })
            else:
                parsed_data.update({
                    'country_ref': None,
                    'house_number': None,
                    'street': None,
                    'town': None,
                    'post_code': None,
                    'postal_region': None
                })

            # Handle TopographicPlaceRef
            topographic_place_ref_elem = place_elem.find('netex:TopographicPlaceRef', ns)
            if topographic_place_ref_elem is not None:
                parsed_data['topographic_place_ref'] = topographic_place_ref_elem.attrib.get('ref')
            else:
                parsed_data['topographic_place_ref'] = None

            # Handle Locale and its subelements
            locale_elem = place_elem.find('netex:Locale', ns)
            if locale_elem is not None:
                time_zone_offset = get_element_text(locale_elem, 'netex:TimeZoneOffset', ns)
                time_zone = get_element_text(locale_elem, 'netex:TimeZone', ns)
                summer_time_zone_offset = get_element_text(locale_elem, 'netex:SummerTimeZoneOffset', ns)
                default_language = get_element_text(locale_elem, 'netex:DefaultLanguage', ns)
                parsed_data.update({
                    'time_zone_offset': time_zone_offset,
                    'time_zone': time_zone,
                    'summer_time_zone_offset': summer_time_zone_offset,
                    'default_language': default_language
                })
            else:
                parsed_data.update({
                    'time_zone_offset': None,
                    'time_zone': None,
                    'summer_time_zone_offset': None,
                    'default_language': None
                })

            # Add composite_frame_id
            parsed_data['composite_frame_id'] = composite_frame.id

            # Create StopPlace instance
            stop_place = StopPlace(**parsed_data)
            session.add(stop_place)
            session.flush()  # To assign an ID to stop_place.id
            # print(f"Inserted StopPlace with ID: {parsed_data['stop_place_id']}")

            # Handle alternativeNames
            alternative_names_elem = place_elem.find('netex:alternativeNames', ns)
            if alternative_names_elem is not None:
                alternative_name_elems = alternative_names_elem.findall('netex:AlternativeName', ns)
                for alt_name_elem in alternative_name_elems:
                    lang = get_element_text(alt_name_elem, 'netex:Lang', ns)
                    name_type = get_element_text(alt_name_elem, 'netex:NameType', ns)
                    type_of_name = get_element_text(alt_name_elem, 'netex:TypeOfName', ns)
                    name = get_element_text(alt_name_elem, 'netex:Name', ns)
                    alternative_name = AlternativeName(
                        lang=lang,
                        name_type=name_type,
                        type_of_name=type_of_name,
                        name=name,
                        stop_place_id=stop_place.id
                    )
                    session.add(alternative_name)
            session.commit()

        except Exception as e:
            print(f"Error inserting StopPlace: {e}")
            session.rollback()

    print("Finished processing StopPlace elements.")

def populate_networks(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    networks = composite_frame_elem.findall('.//netex:ServiceFrame/netex:additionalNetworks/netex:Network', ns)
    print(f"Found {len(networks)} Network elements")

    # Limit the number of networks processed in test mode
    if test_mode:
        networks = networks[:10]

    field_mapping = {
        'id': 'network_id',
        'version': 'version',
        'Name': 'name'
    }

    for network_elem in networks:
        try:
            # Parse the network element
            parsed_data = parse_generic_element(network_elem, field_mapping, ns)
            parsed_data['composite_frame_id'] = composite_frame.id

            # Create Network instance
            network = Network(**parsed_data)
            session.add(network)
            session.flush()  # To assign an ID to network.id
            print(f"Inserted Network with ID: {parsed_data['network_id']}")

            # Parse groupsOfLines
            groups_of_lines_elem = network_elem.find('netex:groupsOfLines', ns)
            if groups_of_lines_elem is not None:
                group_elems = groups_of_lines_elem.findall('netex:GroupOfLines', ns)
                print(f"Found {len(group_elems)} GroupOfLines elements in Network {parsed_data['network_id']}")

                for group_elem in group_elems:
                    group_field_mapping = {
                        'id': 'group_id',
                        'version': 'version',
                        'Name': 'name'
                    }

                    # Parse the group element
                    group_parsed_data = parse_generic_element(group_elem, group_field_mapping, ns)
                    group_parsed_data['network_id'] = network.id

                    # Create GroupOfLines instance
                    group_of_lines = GroupOfLines(**group_parsed_data)
                    session.add(group_of_lines)
                    session.flush()  # To assign an ID to group_of_lines.id
                    print(f"Inserted GroupOfLines with ID: {group_parsed_data['group_id']}")

                    # Parse members/LineRef
                    members_elem = group_elem.find('netex:members', ns)
                    if members_elem is not None:
                        line_ref_elems = members_elem.findall('netex:LineRef', ns)
                        print(f"Found {len(line_ref_elems)} LineRef elements in GroupOfLines {group_parsed_data['group_id']}")

                        for line_ref_elem in line_ref_elems:
                            ref = line_ref_elem.attrib.get('ref')
                            # Create LineRef instance
                            line_ref = LineRef(
                                ref=ref,
                                group_of_lines_id=group_of_lines.id
                            )
                            session.add(line_ref)
                            print(f"Inserted LineRef with ref: {ref}")
            else:
                print(f"No groupsOfLines found in Network {parsed_data['network_id']}")

            session.commit()

        except Exception as e:
            print(f"Error inserting Network or its related elements: {e}")
            session.rollback()

    print("Finished processing Network elements.")


def populate_route_points(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    route_points = composite_frame_elem.findall('.//netex:ServiceFrame/netex:routePoints/netex:RoutePoint', ns)
    print(f"Found {len(route_points)} RoutePoint elements")

    # Limit the number of route points processed in test mode
    if test_mode:
        route_points = route_points[:100]

    field_mapping = {
        'id': 'route_point_id',
        'version': 'version',
    }

    for point_elem in route_points:
        try:
            # Parse attributes and immediate child elements
            parsed_data = parse_generic_element(point_elem, field_mapping, ns)
            parsed_data['composite_frame_id'] = composite_frame.id

            # Handle Location/Longitude and Latitude
            location_elem = point_elem.find('netex:Location', ns)
            if location_elem is not None:
                longitude = get_element_text(location_elem, 'netex:Longitude', ns)
                latitude = get_element_text(location_elem, 'netex:Latitude', ns)
                parsed_data['longitude'] = float(longitude) if longitude else None
                parsed_data['latitude'] = float(latitude) if latitude else None
            else:
                parsed_data['longitude'] = None
                parsed_data['latitude'] = None

            # Create RoutePoint instance
            route_point = RoutePoint(**parsed_data)
            session.add(route_point)
            print(f"Inserted RoutePoint with ID: {parsed_data['route_point_id']}")

        except Exception as e:
            print(f"Error inserting RoutePoint: {e}")
            session.rollback()

    session.commit()

def populate_route_links(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    route_links = composite_frame_elem.findall('.//netex:ServiceFrame/netex:routeLinks/netex:RouteLink', ns)
    print(f"Found {len(route_links)} RouteLink elements")

    # Limit the number of route links processed in test mode
    if test_mode:
        route_links = route_links[:100]

    field_mapping = {
        'id': 'route_link_id',
        'version': 'version',
        'Distance': 'distance',
    }

    for link_elem in route_links:
        try:
            # Parse attributes and immediate child elements
            parsed_data = parse_generic_element(link_elem, field_mapping, ns)
            parsed_data['composite_frame_id'] = composite_frame.id

            # Handle FromPointRef and ToPointRef
            from_point_ref_elem = link_elem.find('netex:FromPointRef', ns)
            parsed_data['from_point_ref'] = from_point_ref_elem.attrib.get('ref') if from_point_ref_elem is not None else None

            to_point_ref_elem = link_elem.find('netex:ToPointRef', ns)
            parsed_data['to_point_ref'] = to_point_ref_elem.attrib.get('ref') if to_point_ref_elem is not None else None

            # Create RouteLink instance
            route_link = RouteLink(**parsed_data)
            session.add(route_link)
            print(f"Inserted RouteLink with ID: {parsed_data['route_link_id']}")

        except Exception as e:
            print(f"Error inserting RouteLink: {e}")
            session.rollback()

    session.commit()

def populate_lines(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    lines = composite_frame_elem.findall('.//netex:ServiceFrame/netex:lines/netex:Line', ns)
    print(f"Found {len(lines)} Line elements")

    # Limit the number of lines processed in test mode
    if test_mode:
        lines = lines[:100]

    field_mapping = {
        'id': 'line_id',
        'version': 'version',
        'responsibilitySetRef': 'responsibility_set_ref',
        'Name': 'name',
        'Description': 'description',
        'TransportMode': 'transport_mode',
        'PublicCode': 'public_code',
    }

    for line_elem in lines:
        try:
            # Parse attributes and immediate child elements
            parsed_data = parse_generic_element(line_elem, field_mapping, ns)
            parsed_data['composite_frame_id'] = composite_frame.id

            # Handle TransportSubmode
            transport_submode_elem = line_elem.find('netex:TransportSubmode', ns)
            if transport_submode_elem is not None:
                # Assume that there's only one child element under TransportSubmode
                for submode_elem in transport_submode_elem:
                    parsed_data['transport_submode'] = submode_elem.text.strip() if submode_elem.text else None
                    break
            else:
                parsed_data['transport_submode'] = None

            # Handle OperatorRef
            operator_ref_elem = line_elem.find('netex:OperatorRef', ns)
            parsed_data['operator_ref'] = operator_ref_elem.attrib.get('ref') if operator_ref_elem is not None else None

            # Create Line instance
            line = Line(**parsed_data)
            session.add(line)
            session.flush()  # To assign an ID to line.id
            print(f"Inserted Line with ID: {parsed_data['line_id']}")

            # Handle routes/RouteRef
            routes_elem = line_elem.find('netex:routes', ns)
            if routes_elem is not None:
                route_ref_elems = routes_elem.findall('netex:RouteRef', ns)
                print(f"Found {len(route_ref_elems)} RouteRef elements in Line {parsed_data['line_id']}")

                for route_ref_elem in route_ref_elems:
                    ref = route_ref_elem.attrib.get('ref')
                    # Create RouteRef instance
                    route_ref = RouteRef(
                        ref=ref,
                        line_id=line.id
                    )
                    session.add(route_ref)
                    print(f"Inserted RouteRef with ref: {ref}")
            else:
                print(f"No routes found in Line {parsed_data['line_id']}")

        except Exception as e:
            print(f"Error inserting Line or its related elements: {e}")
            session.rollback()

    session.commit()

def populate_destination_displays(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    destination_displays = composite_frame_elem.findall('.//netex:ServiceFrame/netex:destinationDisplays/netex:DestinationDisplay', ns)
    print(f"Found {len(destination_displays)} DestinationDisplay elements")

    # Limit the number of destination displays processed in test mode
    if test_mode:
        destination_displays = destination_displays[:100]

    field_mapping = {
        'id': 'destination_display_id',
        'version': 'version',
        'SideText': 'side_text',
        'FrontText': 'front_text',
    }

    for display_elem in destination_displays:
        try:
            # Parse attributes and immediate child elements
            parsed_data = parse_generic_element(display_elem, field_mapping, ns)
            parsed_data['composite_frame_id'] = composite_frame.id

            # Create DestinationDisplay instance
            destination_display = DestinationDisplay(**parsed_data)
            session.add(destination_display)
            print(f"Inserted DestinationDisplay with ID: {parsed_data['destination_display_id']}")

        except Exception as e:
            print(f"Error inserting DestinationDisplay: {e}")
            session.rollback()

    session.commit()


def populate_scheduled_stop_points(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    scheduled_stop_points = composite_frame_elem.findall('.//netex:ServiceFrame/netex:scheduledStopPoints/netex:ScheduledStopPoint', ns)
    print(f"Found {len(scheduled_stop_points)} ScheduledStopPoint elements")

    if test_mode:
        scheduled_stop_points = scheduled_stop_points[:100]

    field_mapping = {
        'id': 'scheduled_stop_point_id',
        'version': 'version',
        'Name': 'name',
        'PublicCode': 'public_code',
    }

    for point_elem in scheduled_stop_points:
        try:
            parsed_data = parse_generic_element(point_elem, field_mapping, ns)
            parsed_data['composite_frame_id'] = composite_frame.id

            # Handle Name element's lang attribute
            name_elem = point_elem.find('netex:Name', ns)
            parsed_data['lang'] = name_elem.attrib.get('lang') if name_elem is not None else None

            # Handle Location/Longitude and Latitude
            location_elem = point_elem.find('netex:Location', ns)
            if location_elem is not None:
                longitude = get_element_text(location_elem, 'netex:Longitude', ns)
                latitude = get_element_text(location_elem, 'netex:Latitude', ns)
                parsed_data['longitude'] = float(longitude) if longitude else None
                parsed_data['latitude'] = float(latitude) if latitude else None
            else:
                parsed_data['longitude'] = None
                parsed_data['latitude'] = None

            # Create ScheduledStopPoint instance
            scheduled_stop_point = ScheduledStopPoint(**parsed_data)
            session.add(scheduled_stop_point)
            print(f"Inserted ScheduledStopPoint with ID: {parsed_data['scheduled_stop_point_id']}")

        except Exception as e:
            print(f"Error inserting ScheduledStopPoint: {e}")
            session.rollback()

    session.commit()


def populate_connections(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    connections = composite_frame_elem.findall('.//netex:ServiceFrame/netex:connections/netex:Connection', ns)
    print(f"Found {len(connections)} Connection elements")

    if test_mode:
        connections = connections[:100]

    field_mapping = {
        'id': 'connection_id',
        'version': 'version',
        'Name': 'name',
        'BothWays': 'both_ways',
    }

    for conn_elem in connections:
        try:
            parsed_data = parse_generic_element(conn_elem, field_mapping, ns)
            parsed_data['composite_frame_id'] = composite_frame.id

            # Convert BothWays to boolean
            parsed_data['both_ways'] = bool(int(parsed_data['both_ways'])) if parsed_data['both_ways'] else None

            # Handle WalkTransferDuration/DefaultDuration
            duration_elem = conn_elem.find('netex:WalkTransferDuration/netex:DefaultDuration', ns)
            parsed_data['default_duration'] = duration_elem.text.strip() if duration_elem is not None else None

            # Handle From/ScheduledStopPointRef
            from_elem = conn_elem.find('netex:From/netex:ScheduledStopPointRef', ns)
            parsed_data['from_scheduled_stop_point_ref'] = from_elem.attrib.get('ref') if from_elem is not None else None

            # Handle To/ScheduledStopPointRef
            to_elem = conn_elem.find('netex:To/netex:ScheduledStopPointRef', ns)
            parsed_data['to_scheduled_stop_point_ref'] = to_elem.attrib.get('ref') if to_elem is not None else None

            # Create Connection instance
            connection = Connection(**parsed_data)
            session.add(connection)
            print(f"Inserted Connection with ID: {parsed_data['connection_id']}")

        except Exception as e:
            print(f"Error inserting Connection: {e}")
            session.rollback()

    session.commit()


def populate_default_connections(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    default_connections = composite_frame_elem.findall('.//netex:ServiceFrame/netex:connections/netex:DefaultConnection', ns)
    print(f"Found {len(default_connections)} DefaultConnection elements")

    if test_mode:
        default_connections = default_connections[:100]

    field_mapping = {
        'id': 'default_connection_id',
        'version': 'version',
        'BothWays': 'both_ways',
    }

    for conn_elem in default_connections:
        try:
            parsed_data = parse_generic_element(conn_elem, field_mapping, ns)
            parsed_data['composite_frame_id'] = composite_frame.id

            # Convert BothWays to boolean
            parsed_data['both_ways'] = bool(int(parsed_data['both_ways'])) if parsed_data['both_ways'] else None

            # Handle WalkTransferDuration/DefaultDuration
            duration_elem = conn_elem.find('netex:WalkTransferDuration/netex:DefaultDuration', ns)
            parsed_data['default_duration'] = duration_elem.text.strip() if duration_elem is not None else None

            # Handle From/TransportMode
            from_elem = conn_elem.find('netex:From/netex:TransportMode', ns)
            parsed_data['from_transport_mode'] = from_elem.text.strip() if from_elem is not None else None

            # Handle To/TransportMode
            to_elem = conn_elem.find('netex:To/netex:TransportMode', ns)
            parsed_data['to_transport_mode'] = to_elem.text.strip() if to_elem is not None else None

            # Create DefaultConnection instance
            default_connection = DefaultConnection(**parsed_data)
            session.add(default_connection)
            print(f"Inserted DefaultConnection with ID: {parsed_data['default_connection_id']}")

        except Exception as e:
            print(f"Error inserting DefaultConnection: {e}")
            session.rollback()

    session.commit()


def populate_passenger_stop_assignments(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    assignments = composite_frame_elem.findall('.//netex:ServiceFrame/netex:stopAssignments/netex:PassengerStopAssignment', ns)
    print(f"Found {len(assignments)} PassengerStopAssignment elements")

    if test_mode:
        assignments = assignments[:100]

    field_mapping = {
        'id': 'assignment_id',
        'version': 'version',
        'order': 'order',
    }

    for assignment_elem in assignments:
        try:
            parsed_data = parse_generic_element(assignment_elem, field_mapping, ns)
            parsed_data['composite_frame_id'] = composite_frame.id

            # Handle ScheduledStopPointRef
            scheduled_stop_point_ref_elem = assignment_elem.find('netex:ScheduledStopPointRef', ns)
            parsed_data['scheduled_stop_point_ref'] = scheduled_stop_point_ref_elem.attrib.get('ref') if scheduled_stop_point_ref_elem is not None else None

            # Handle StopPlaceRef
            stop_place_ref_elem = assignment_elem.find('netex:StopPlaceRef', ns)
            parsed_data['stop_place_ref'] = stop_place_ref_elem.attrib.get('ref') if stop_place_ref_elem is not None else None

            # Create PassengerStopAssignment instance
            assignment = PassengerStopAssignment(**parsed_data)
            session.add(assignment)
            print(f"Inserted PassengerStopAssignment with ID: {parsed_data['assignment_id']}")

        except Exception as e:
            print(f"Error inserting PassengerStopAssignment: {e}")
            session.rollback()

    session.commit()


def populate_service_journey_patterns(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    patterns = composite_frame_elem.findall('.//netex:ServiceFrame/netex:journeyPatterns/netex:ServiceJourneyPattern', ns)
    print(f"Found {len(patterns)} ServiceJourneyPattern elements")

    if test_mode:
        patterns = patterns[:100]

    field_mapping = {
        'id': 'journey_pattern_id',
        'version': 'version',
        'Distance': 'distance',
        'ServiceJourneyPatternType': 'service_journey_pattern_type',
    }

    for pattern_elem in patterns:
        try:
            parsed_data = parse_generic_element(pattern_elem, field_mapping, ns)
            parsed_data['composite_frame_id'] = composite_frame.id

            # Handle DestinationDisplayRef
            dest_display_ref_elem = pattern_elem.find('netex:DestinationDisplayRef', ns)
            parsed_data['destination_display_ref'] = dest_display_ref_elem.attrib.get('ref') if dest_display_ref_elem is not None else None

            # Create ServiceJourneyPattern instance
            pattern = ServiceJourneyPattern(**parsed_data)
            session.add(pattern)
            session.flush()  # To assign pattern.id

            # Handle pointsInSequence/StopPointInJourneyPattern
            points_in_sequence_elem = pattern_elem.find('netex:pointsInSequence', ns)
            if points_in_sequence_elem is not None:
                stop_point_elems = points_in_sequence_elem.findall('netex:StopPointInJourneyPattern', ns)
                for stop_point_elem in stop_point_elems:
                    stop_point_data = {
                        'stop_point_id': stop_point_elem.attrib.get('id'),
                        'version': stop_point_elem.attrib.get('version'),
                        'order': int(stop_point_elem.attrib.get('order')) if stop_point_elem.attrib.get('order') else None,
                        'journey_pattern_id': pattern.id,
                    }

                    # Handle ScheduledStopPointRef
                    scheduled_stop_point_ref_elem = stop_point_elem.find('netex:ScheduledStopPointRef', ns)
                    stop_point_data['scheduled_stop_point_ref'] = scheduled_stop_point_ref_elem.attrib.get('ref') if scheduled_stop_point_ref_elem is not None else None

                    # Create StopPointInJourneyPattern instance
                    stop_point = StopPointInJourneyPattern(**stop_point_data)
                    session.add(stop_point)

            session.commit()
            print(f"Inserted ServiceJourneyPattern with ID: {parsed_data['journey_pattern_id']}")

        except Exception as e:
            print(f"Error inserting ServiceJourneyPattern: {e}")
            session.rollback()

    session.commit()


def populate_day_types(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    day_types = composite_frame_elem.findall('.//netex:ServiceCalendarFrame/netex:dayTypes/netex:DayType', ns)
    print(f"Found {len(day_types)} DayType elements")

    if test_mode:
        day_types = day_types[:100]

    field_mapping = {
        'id': 'day_type_id',
        'version': 'version',
    }

    for day_type_elem in day_types:
        try:
            parsed_data = parse_generic_element(day_type_elem, field_mapping, ns)
            parsed_data['composite_frame_id'] = composite_frame.id

            # Create DayType instance
            day_type = DayType(**parsed_data)
            session.add(day_type)
            print(f"Inserted DayType with ID: {parsed_data['day_type_id']}")

        except Exception as e:
            print(f"Error inserting DayType: {e}")
            session.rollback()

    session.commit()

def populate_uic_operating_periods(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    periods = composite_frame_elem.findall('.//netex:ServiceCalendarFrame/netex:operatingPeriods/netex:UicOperatingPeriod', ns)
    print(f"Found {len(periods)} UicOperatingPeriod elements")

    if test_mode:
        periods = periods[:100]

    field_mapping = {
        'id': 'operating_period_id',
        'version': 'version',
        'FromDate': 'from_date',
        'ToDate': 'to_date',
        'ValidDayBits': 'valid_day_bits',
    }

    for period_elem in periods:
        try:
            parsed_data = parse_generic_element(period_elem, field_mapping, ns)
            parsed_data['composite_frame_id'] = composite_frame.id

            # Convert dates
            if parsed_data.get('from_date'):
                parsed_data['from_date'] = datetime.fromisoformat(parsed_data['from_date'])
            if parsed_data.get('to_date'):
                parsed_data['to_date'] = datetime.fromisoformat(parsed_data['to_date'])

            uic_operating_period = UicOperatingPeriod(**parsed_data)
            session.add(uic_operating_period)
            print(f"Inserted UicOperatingPeriod with ID: {parsed_data['operating_period_id']}")

        except Exception as e:
            print(f"Error inserting UicOperatingPeriod: {e}")
            session.rollback()

    session.commit()


def populate_day_type_assignments(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    assignments = composite_frame_elem.findall('.//netex:ServiceCalendarFrame/netex:dayTypeAssignments/netex:DayTypeAssignment', ns)
    print(f"Found {len(assignments)} DayTypeAssignment elements")

    if test_mode:
        assignments = assignments[:100]

    field_mapping = {
        'id': 'assignment_id',
        'version': 'version',
        'order': 'order',
    }

    for assignment_elem in assignments:
        try:
            parsed_data = parse_generic_element(assignment_elem, field_mapping, ns)
            parsed_data['composite_frame_id'] = composite_frame.id

            # Handle UicOperatingPeriodRef
            uic_op_ref_elem = assignment_elem.find('netex:UicOperatingPeriodRef', ns)
            parsed_data['uic_operating_period_ref'] = uic_op_ref_elem.attrib.get('ref') if uic_op_ref_elem is not None else None

            # Handle DayTypeRef
            day_type_ref_elem = assignment_elem.find('netex:DayTypeRef', ns)
            parsed_data['day_type_ref'] = day_type_ref_elem.attrib.get('ref') if day_type_ref_elem is not None else None

            day_type_assignment = DayTypeAssignment(**parsed_data)
            session.add(day_type_assignment)
            print(f"Inserted DayTypeAssignment with ID: {parsed_data['assignment_id']}")

        except Exception as e:
            print(f"Error inserting DayTypeAssignment: {e}")
            session.rollback()

    session.commit()


def populate_service_journeys(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    journeys = composite_frame_elem.findall('.//netex:TimetableFrame/netex:vehicleJourneys/netex:ServiceJourney', ns)
    print(f"Found {len(journeys)} ServiceJourney elements")

    if test_mode:
        journeys = journeys[:100]

    field_mapping = {
        'id': 'service_journey_id',
        'version': 'version',
        'responsibilitySetRef': 'responsibility_set_ref',
        'dataSourceRef': 'data_source_ref',
        'changed': 'changed',
        'status': 'status',
    }

    for journey_elem in journeys:
        try:
            parsed_data = parse_generic_element(journey_elem, field_mapping, ns)
            parsed_data['composite_frame_id'] = composite_frame.id

            # Convert 'changed' to datetime
            if parsed_data.get('changed'):
                parsed_data['changed'] = datetime.fromisoformat(parsed_data['changed'])

            # Handle ValidBetween
            valid_between_elem = journey_elem.find('netex:ValidBetween', ns)
            if valid_between_elem is not None:
                from_date = get_element_text(valid_between_elem, 'netex:FromDate', ns)
                to_date = get_element_text(valid_between_elem, 'netex:ToDate', ns)
                parsed_data['valid_from_date'] = datetime.fromisoformat(from_date) if from_date else None
                parsed_data['valid_to_date'] = datetime.fromisoformat(to_date) if to_date else None
            else:
                parsed_data['valid_from_date'] = None
                parsed_data['valid_to_date'] = None

            # Handle BrandingRef
            branding_ref_elem = journey_elem.find('netex:BrandingRef', ns)
            parsed_data['branding_ref'] = branding_ref_elem.attrib.get('ref') if branding_ref_elem is not None else None

            # Handle other child elements
            parsed_data['distance'] = get_element_text(journey_elem, 'netex:Distance', ns)
            parsed_data['transport_mode'] = get_element_text(journey_elem, 'netex:TransportMode', ns)
            parsed_data['service_alteration'] = get_element_text(journey_elem, 'netex:ServiceAlteration', ns)
            parsed_data['departure_time'] = get_element_text(journey_elem, 'netex:DepartureTime', ns)

            # Handle TransportSubmode/RailSubmode
            transport_submode_elem = journey_elem.find('netex:TransportSubmode', ns)
            if transport_submode_elem is not None:
                for submode_elem in transport_submode_elem:
                    parsed_data['transport_submode'] = submode_elem.text.strip() if submode_elem.text else None
                    break
            else:
                parsed_data['transport_submode'] = None

            # Handle DayTypeRefs
            day_types_elem = journey_elem.find('netex:dayTypes', ns)
            day_type_refs = []
            if day_types_elem is not None:
                day_type_ref_elems = day_types_elem.findall('netex:DayTypeRef', ns)
                for day_type_ref_elem in day_type_ref_elems:
                    day_type_ref = DayTypeRef(
                        ref=day_type_ref_elem.attrib.get('ref'),
                        service_journey_id=None  # Will assign after ServiceJourney is created
                    )
                    day_type_refs.append(day_type_ref)

            # Handle JourneyPatternRef
            journey_pattern_ref_elem = journey_elem.find('netex:JourneyPatternRef', ns)
            parsed_data['journey_pattern_ref'] = journey_pattern_ref_elem.attrib.get('ref') if journey_pattern_ref_elem is not None else None

            # Handle OperatorRef
            operator_ref_elem = journey_elem.find('netex:OperatorRef', ns)
            parsed_data['operator_ref'] = operator_ref_elem.attrib.get('ref') if operator_ref_elem is not None else None

            # Handle LineRef
            line_ref_elem = journey_elem.find('netex:LineRef', ns)
            parsed_data['line_ref'] = line_ref_elem.attrib.get('ref') if line_ref_elem is not None else None

            # Create ServiceJourney instance
            service_journey = ServiceJourney(**parsed_data)
            session.add(service_journey)
            session.flush()  # To assign service_journey.id

            # Assign service_journey_id to DayTypeRefs
            for day_type_ref in day_type_refs:
                day_type_ref.service_journey_id = service_journey.id
                session.add(day_type_ref)

            # Handle trainNumbers/TrainNumberRef
            train_numbers_elem = journey_elem.find('netex:trainNumbers', ns)
            if train_numbers_elem is not None:
                train_number_ref_elems = train_numbers_elem.findall('netex:TrainNumberRef', ns)
                for train_number_ref_elem in train_number_ref_elems:
                    train_number_ref = TrainNumberRef(
                        ref=train_number_ref_elem.attrib.get('ref'),
                        version=train_number_ref_elem.attrib.get('version'),
                        service_journey_id=service_journey.id
                    )
                    session.add(train_number_ref)

            # Handle passingTimes/TimetabledPassingTime
            passing_times_elem = journey_elem.find('netex:passingTimes', ns)
            if passing_times_elem is not None:
                passing_time_elems = passing_times_elem.findall('netex:TimetabledPassingTime', ns)
                for passing_time_elem in passing_time_elems:
                    point_ref_elem = passing_time_elem.find('netex:PointInJourneyPatternRef', ns)
                    point_ref = point_ref_elem.attrib.get('ref') if point_ref_elem is not None else None
                    arrival_time = get_element_text(passing_time_elem, 'netex:ArrivalTime', ns)
                    departure_time = get_element_text(passing_time_elem, 'netex:DepartureTime', ns)

                    passing_time = TimetabledPassingTime(
                        point_in_journey_pattern_ref=point_ref,
                        arrival_time=arrival_time,
                        departure_time=departure_time,
                        service_journey_id=service_journey.id
                    )
                    session.add(passing_time)

            # Handle facilities/ServiceFacilitySet
            facilities_elem = journey_elem.find('netex:facilities/netex:ServiceFacilitySet', ns)
            if facilities_elem is not None:
                facility_field_mapping = {
                    'id': 'facility_set_id',
                    'version': 'version',
                    'FareClasses': 'fare_classes',
                    'AccommodationFacilityList': 'accommodation_facility_list',
                    'LuggageCarriageFacilityList': 'luggage_carriage_facility_list',
                    'ServiceReservationFacilityList': 'service_reservation_facility_list',
                }
                facility_parsed_data = parse_generic_element(facilities_elem, facility_field_mapping, ns)
                facility_parsed_data['service_journey_id'] = service_journey.id
                facility = ServiceFacilitySet(**facility_parsed_data)
                session.add(facility)

            session.commit()
            print(f"Inserted ServiceJourney with ID: {parsed_data['service_journey_id']}")

        except Exception as e:
            print(f"Error inserting ServiceJourney: {e}")
            session.rollback()

    session.commit()


def populate_train_numbers(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    train_numbers = composite_frame_elem.findall('.//netex:ResourceFrame/netex:trainNumbers/netex:TrainNumber', ns)
    print(f"Found {len(train_numbers)} TrainNumber elements")

    if test_mode:
        train_numbers = train_numbers[:100]

    field_mapping = {
        'id': 'train_number_id',
        'version': 'version',
        'responsibilitySetRef': 'responsibility_set_ref',
        'ForAdvertisement': 'for_advertisement',
    }

    for train_number_elem in train_numbers:
        try:
            parsed_data = parse_generic_element(train_number_elem, field_mapping, ns)
            parsed_data['composite_frame_id'] = composite_frame.id

            # Create TrainNumber instance
            train_number = TrainNumber(**parsed_data)
            session.add(train_number)
            print(f"Inserted TrainNumber with ID: {parsed_data['train_number_id']}")

        except Exception as e:
            print(f"Error inserting TrainNumber: {e}")
            session.rollback()

    session.commit()


def populate_journey_part_couples(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    journey_part_couples = composite_frame_elem.findall('.//netex:GeneralFrame/netex:members/netex:JourneyPartCouple', ns)
    print(f"Found {len(journey_part_couples)} JourneyPartCouple elements")

    if test_mode:
        journey_part_couples = journey_part_couples[:100]

    field_mapping = {
        'id': 'journey_part_couple_id',
        'version': 'version',
        'order': 'order',
        'StartTime': 'start_time',
        'StartTimeDayOffset': 'start_time_day_offset',
        'EndTime': 'end_time',
        'EndTimeDayOffset': 'end_time_day_offset',
    }

    for couple_elem in journey_part_couples:
        try:
            parsed_data = parse_generic_element(couple_elem, field_mapping, ns)
            parsed_data['composite_frame_id'] = composite_frame.id

            # Handle FromStopPointRef
            from_stop_point_ref_elem = couple_elem.find('netex:FromStopPointRef', ns)
            parsed_data['from_stop_point_ref'] = from_stop_point_ref_elem.attrib.get('ref') if from_stop_point_ref_elem is not None else None

            # Handle ToStopPointRef
            to_stop_point_ref_elem = couple_elem.find('netex:ToStopPointRef', ns)
            parsed_data['to_stop_point_ref'] = to_stop_point_ref_elem.attrib.get('ref') if to_stop_point_ref_elem is not None else None

            # Handle MainPartRef
            main_part_ref_elem = couple_elem.find('netex:MainPartRef', ns)
            parsed_data['main_part_ref'] = main_part_ref_elem.attrib.get('ref') if main_part_ref_elem is not None else None

            # Handle TrainNumberRef
            train_number_ref_elem = couple_elem.find('netex:TrainNumberRef', ns)
            parsed_data['train_number_ref'] = train_number_ref_elem.attrib.get('ref') if train_number_ref_elem is not None else None

            # Create JourneyPartCouple instance
            journey_part_couple = JourneyPartCouple(**parsed_data)
            session.add(journey_part_couple)
            session.flush()  # To assign journey_part_couple.id

            # Handle journeyParts/JourneyPartRef
            journey_parts_elem = couple_elem.find('netex:journeyParts', ns)
            if journey_parts_elem is not None:
                journey_part_ref_elems = journey_parts_elem.findall('netex:JourneyPartRef', ns)
                for journey_part_ref_elem in journey_part_ref_elems:
                    ref = journey_part_ref_elem.attrib.get('ref')
                    version = journey_part_ref_elem.attrib.get('version')
                    journey_part_ref = JourneyPartRef(
                        ref=ref,
                        version=version,
                        journey_part_couple_id=journey_part_couple.id
                    )
                    session.add(journey_part_ref)

            session.commit()
            print(f"Inserted JourneyPartCouple with ID: {parsed_data['journey_part_couple_id']}")

        except Exception as e:
            print(f"Error inserting JourneyPartCouple: {e}")
            session.rollback()

    session.commit()


def populate_coupled_journeys(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    coupled_journeys = composite_frame_elem.findall('.//netex:GeneralFrame/netex:members/netex:CoupledJourney', ns)
    print(f"Found {len(coupled_journeys)} CoupledJourney elements")

    if test_mode:
        coupled_journeys = coupled_journeys[:100]

    field_mapping = {
        'id': 'coupled_journey_id',
        'version': 'version',
    }

    for coupled_journey_elem in coupled_journeys:
        try:
            parsed_data = parse_generic_element(coupled_journey_elem, field_mapping, ns)
            parsed_data['composite_frame_id'] = composite_frame.id

            # Create CoupledJourney instance
            coupled_journey = CoupledJourney(**parsed_data)
            session.add(coupled_journey)
            session.flush()  # To assign coupled_journey.id

            # Handle journeys/VehicleJourneyRef
            journeys_elem = coupled_journey_elem.find('netex:journeys', ns)
            if journeys_elem is not None:
                vehicle_journey_ref_elems = journeys_elem.findall('netex:VehicleJourneyRef', ns)
                for vehicle_journey_ref_elem in vehicle_journey_ref_elems:
                    ref = vehicle_journey_ref_elem.attrib.get('ref')
                    version = vehicle_journey_ref_elem.attrib.get('version')
                    vehicle_journey_ref = VehicleJourneyRef(
                        ref=ref,
                        version=version,
                        coupled_journey_id=coupled_journey.id
                    )
                    session.add(vehicle_journey_ref)

            session.commit()
            print(f"Inserted CoupledJourney with ID: {parsed_data['coupled_journey_id']}")

        except Exception as e:
            print(f"Error inserting CoupledJourney: {e}")
            session.rollback()

    session.commit()


def populate_types_of_service(composite_frame, composite_frame_elem, session, ns, test_mode=False):
    types_of_service = composite_frame_elem.findall('.//netex:ResourceFrame/netex:typesOfService/netex:TypeOfService', ns)
    print(f"Found {len(types_of_service)} TypeOfService elements")

    if test_mode:
        types_of_service = types_of_service[:100]

    field_mapping = {
        'id': 'type_of_service_id',
        'version': 'version',
        'PrivateCode': 'private_code',
    }

    for type_elem in types_of_service:
        try:
            parsed_data = parse_generic_element(type_elem, field_mapping, ns)
            parsed_data['composite_frame_id'] = composite_frame.id

            # Handle Name
            name_elem = type_elem.find('netex:Name', ns)
            if name_elem is not None:
                parsed_data['name'] = name_elem.text.strip() if name_elem.text else None
                parsed_data['name_lang'] = name_elem.attrib.get('lang')
            else:
                parsed_data['name'] = None
                parsed_data['name_lang'] = None

            # Handle ShortName
            short_name_elem = type_elem.find('netex:ShortName', ns)
            if short_name_elem is not None:
                parsed_data['short_name'] = short_name_elem.text.strip() if short_name_elem.text else None
                parsed_data['short_name_lang'] = short_name_elem.attrib.get('lang')
            else:
                parsed_data['short_name'] = None
                parsed_data['short_name_lang'] = None

            # Create TypeOfService instance
            type_of_service = TypeOfService(**parsed_data)
            session.add(type_of_service)
            print(f"Inserted TypeOfService with ID: {parsed_data['type_of_service_id']}")

        except Exception as e:
            print(f"Error inserting TypeOfService: {e}")
            session.rollback()

    session.commit()







