import ssl
import certifi
ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
import os
from libsql_client import create_client_sync

TURSO_DATABASE_URL = os.environ["TURSO_DATABASE_URL"]
TURSO_AUTH_TOKEN = os.environ["TURSO_AUTH_TOKEN"]

db = create_client_sync(
    url=TURSO_DATABASE_URL,
    auth_token=TURSO_AUTH_TOKEN
)

def fetch_all(query: str, params=()):
    result = db.execute(query, params)
    return result.rows
