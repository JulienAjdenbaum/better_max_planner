import xml.etree.ElementTree as ET

def extract_journey_parts(xml_file, element='JourneyPart', max_examples=5):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Extract the namespace from the root tag dynamically
        ns = {'netex': root.tag[root.tag.find("{")+1:root.tag.find("}")]}

        # Find JourneyPart elements in the XML file
        journey_parts = root.findall(f".//netex:{element}", ns)
        print(f"Found {len(journey_parts)} {element} elements")

        # Limit to max_examples for demonstration purposes
        if len(journey_parts) == 0:
            print("No {element} elements found. Please verify the XML structure and namespaces.")

        for i, journey_part in enumerate(journey_parts[:max_examples]):
            print(f"{element} #{i + 1}:")
            print(ET.tostring(journey_part, encoding='unicode'))
            print("-" * 40)

    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
    except Exception as e:
        print(f"Error: {e}")

# Use the function on your XML file
extract_journey_parts("../../../data/netex_xml/sncf_netexfr_20241018_2327.xml", element="TypeOfService")
