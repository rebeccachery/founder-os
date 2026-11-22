import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

from lib.db import get_connection


@contextmanager
def db_session() -> Generator[sqlite3.Connection, None, None]:
    with get_connection() as conn:
        yield conn
