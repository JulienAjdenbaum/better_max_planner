import xml.etree.ElementTree as ET
from collections import defaultdict

def reduce_xml_elements(xml_file, output_file, max_elements=2):
    try:
        # Parse the original XML file
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Dictionary to count elements by their tag path
        element_count = defaultdict(int)

        def traverse_and_limit_elements(element, path=""):
            """Recursively traverse the XML tree and limit elements to max_elements per path."""
            # Update the current path
            current_path = f"{path}/{element.tag}"
            element_count[current_path] += 1

            # Remove elements if they exceed the allowed number of occurrences
            if element_count[current_path] > max_elements:
                return False  # This element should be removed

            # Recursively process children
            children_to_remove = []
            for child in element:
                if not traverse_and_limit_elements(child, current_path):
                    children_to_remove.append(child)

            # Remove the children that exceed the limit
            for child in children_to_remove:
                element.remove(child)

            return True

        # Start the recursive process from the root
        traverse_and_limit_elements(root)

        # Write the reduced XML to a new file
        tree.write(output_file, encoding="utf-8", xml_declaration=True)
        print(f"Reduced XML saved to {output_file}")

    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
    except Exception as e:
        print(f"Error: {e}")

# Use the function to reduce the XML and save the reduced version
input_xml_file = "../../../data/netex_xml/sncf_netexfr_20241018_2327.xml"
output_xml_file = "../../../data/test_xmls/xml_reduced.xml"
reduce_xml_elements(input_xml_file, output_xml_file, max_elements=2)