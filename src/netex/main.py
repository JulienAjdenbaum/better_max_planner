import os
import argparse
from xml_parser import populate_database
from database import get_session, reset_db

def process_files(directory, reset=False, test_mode=False):
    session = get_session()

    if reset:
        reset_db()

    # Iterate over all XML files in the directory
    for filename in os.listdir(directory):
        if filename.endswith(".xml"):
            file_path = os.path.join(directory, filename)
            print(f"Processing file: {file_path}")
            populate_database(file_path, session, test_mode)

    print("All files processed.")

def main():
    parser = argparse.ArgumentParser(description='Process NetEx XML files and store in SQLite database.')
    parser.add_argument('--directory', type=str, required=True, help='Directory containing NetEx XML files.')
    parser.add_argument('--reset', action='store_true', help='Reset the database before processing files.')
    parser.add_argument('--test', action='store_true', help='Run in test mode (limit routes to 100).')
    args = parser.parse_args()

    process_files(args.directory, reset=args.reset, test_mode=args.test)

if __name__ == "__main__":
    main()
