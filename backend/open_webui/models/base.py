from open_webui.env import DATABASE_SCHEMA
from sqlalchemy import MetaData
from sqlalchemy.orm import declarative_base

"""
Defines the Base of all of the models used in the Database.

Allows for defining the schema used by setting the DATABASE_SCHEMA environment variable.
NOTE: This may not work as only the Auth model is created through the use of the model and others are created via SQLAlchemy migration script.
"""

metadata_obj = MetaData(schema=DATABASE_SCHEMA)
Base = declarative_base(metadata=metadata_obj)
