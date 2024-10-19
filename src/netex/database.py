from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
import os

DATABASE_PATH = '/home/julien/Documents/pythonProjects/data/netex.db'
DATABASE_URL = f'sqlite:///{DATABASE_PATH}'

def get_engine():
    return create_engine(DATABASE_URL)

def create_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("Database schema created.")

def reset_db():
    # Delete the existing database file if it exists
    if os.path.exists(DATABASE_PATH):
        os.remove(DATABASE_PATH)
        print(f"Deleted existing database file at {DATABASE_PATH}")
    else:
        print(f"No existing database file to delete at {DATABASE_PATH}")

    # Create a new database
    create_db()

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
