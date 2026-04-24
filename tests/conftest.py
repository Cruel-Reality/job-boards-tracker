import os

# Must be set before any app module is imported so db.py does not raise ValueError.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost/testdb")
