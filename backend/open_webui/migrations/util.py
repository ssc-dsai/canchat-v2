from alembic import op
from sqlalchemy import inspect


def get_existing_tables():
    con = op.get_bind()
    inspector = inspect(con)
    tables = set(inspector.get_table_names())
    return tables


def get_revision_id():
    import uuid

    return str(uuid.uuid4()).replace("-", "")[:12]
