import sqlite3
from contextlib import contextmanager
from typing import Generator

from lib.db import get_connection


@contextmanager
def db_session() -> Generator[sqlite3.Connection, None, None]:
    with get_connection() as conn:
        yield conn
