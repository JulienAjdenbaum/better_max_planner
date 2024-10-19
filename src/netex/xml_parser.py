from models import (
    PublicationDelivery, PublicationTimestamp, ParticipantRef, Description,
    CompositeFrame, ValidBetween, FrameDefaults, ServiceJourney,
    Route, PointOnRoute
)
from datetime import datetime
import xml.etree.ElementTree as ET
from tqdm import tqdm

def find_element_debug(root, path, ns):
    """Helper function to find an element with debugging output."""
    elem = root.find(path, ns)
    if elem is not None and elem.text is not None:
        print(f"Found element: {path} -> {elem.text.strip()}")
    elif elem is not None:
        print(f"Found element: {path} -> No Text")
    else:
        print(f"Element not found: {path}")
    return elem

def get_element_text(element, path, ns):
    """Helper function to extract text from an element."""
    child = element.find(path, ns)
    if child is not None and child.text:
        return child.text.strip()
    return None

def populate_database(xml_file, session, test_mode=False):
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

        # Insert CompositeFrame and nested elements
        composite_frames = root.findall('.//netex:CompositeFrame', ns)
        print(f"Found {len(composite_frames)} CompositeFrame elements")
        for composite_frame_elem in tqdm(composite_frames, desc="Processing CompositeFrames"):
            if composite_frame_elem is not None:
                composite_frame = CompositeFrame(
                    frame_id=composite_frame_elem.attrib.get('id'),
                    version=composite_frame_elem.attrib.get('version'),
                    publication_delivery_id=publication_delivery.id
                )
                session.add(composite_frame)
                session.commit()
                print(f"Inserted CompositeFrame with ID: {composite_frame.frame_id}")

                # Insert Route and Points in Sequence
                routes = composite_frame_elem.findall('.//netex:Route', ns)
                print(f"Found {len(routes)} Route elements in CompositeFrame {composite_frame.frame_id}")

                # Limit the number of routes to 100 if test mode is enabled
                if test_mode and len(routes) > 100:
                    routes = routes[:100]

                # Add a single progress bar for all routes under this composite frame
                with tqdm(total=len(routes), desc="Processing Routes", leave=True) as pbar_routes:
                    for route_elem in routes:
                        try:
                            route_id = route_elem.attrib.get('id')
                            version = route_elem.attrib.get('version')
                            distance = get_element_text(route_elem, 'netex:Distance', ns)
                            line_ref_elem = route_elem.find('netex:LineRef', ns)
                            line_ref = line_ref_elem.attrib.get('ref') if line_ref_elem is not None else None
                            direction_type = get_element_text(route_elem, 'netex:DirectionType', ns)

                            if route_id is None:
                                print(f"Warning: Route element missing ID. Skipping.")
                                pbar_routes.update(1)
                                continue

                            route = Route(
                                route_id=route_id,
                                version=version,
                                distance=int(distance) if distance is not None else None,
                                line_ref=line_ref,
                                direction_type=direction_type,
                                composite_frame_id=composite_frame.id
                            )
                            session.add(route)

                            # Insert PointOnRoute elements
                            points = route_elem.findall('.//netex:PointOnRoute', ns)
                            print(f"Found {len(points)} PointOnRoute elements in Route {route_id}")
                            for point_elem in points:
                                point_id = point_elem.attrib.get('id')
                                version = point_elem.attrib.get('version')
                                order = point_elem.attrib.get('order')
                                route_point_ref_elem = point_elem.find('netex:RoutePointRef', ns)
                                route_point_ref = route_point_ref_elem.attrib.get('ref') if route_point_ref_elem is not None else None

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
                                print(f"Inserted PointOnRoute with ID: {point_id}")

                            # Update progress bar for routes
                            pbar_routes.update(1)

                        except Exception as e:
                            print(f"Error inserting Route or PointOnRoute: {e}")
                            session.rollback()

        # Commit after all inserts for better performance
        try:
            session.commit()
            print(f"Data from {xml_file} inserted into the database.\n")
        except Exception as e:
            print(f"Error committing data to the database: {e}")
            session.rollback()

    except Exception as e:
        print(f"Error processing file {xml_file}: {e}")

