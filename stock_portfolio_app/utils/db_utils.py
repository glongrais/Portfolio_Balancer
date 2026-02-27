import sqlite3
import time
import logging
import os
from contextlib import contextmanager

logger = logging.getLogger(__name__)

SLOW_QUERY_THRESHOLD_MS = float(os.environ.get('SLOW_QUERY_THRESHOLD_MS', '100'))

REQUIRED_TABLES = ['stocks', 'positions', 'transactions', 'historicalstocks', 'historicaldividends', 'deposits', 'net_worth_assets', 'net_worth_snapshots']
REQUIRED_VIEWS = ['mar__stocks', 'int__portfolio_value_evolution', 'int__portfolio_dividends_total', 'int__transactions_dividends']


class TimedCursor:
    """Wraps a sqlite3 cursor to log slow queries."""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, parameters=()):
        start = time.perf_counter()
        result = self._cursor.execute(sql, parameters)
        elapsed_ms = (time.perf_counter() - start) * 1000
        if elapsed_ms >= SLOW_QUERY_THRESHOLD_MS:
            logger.warning("Slow query (%.1fms): %s", elapsed_ms, sql.strip()[:200])
        return result

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def description(self):
        return self._cursor.description


class TimedConnection:
    """Wraps a sqlite3 connection to return TimedCursors and log slow queries on direct execute()."""

    def __init__(self, connection):
        self._connection = connection

    def execute(self, sql, parameters=()):
        start = time.perf_counter()
        result = self._connection.execute(sql, parameters)
        elapsed_ms = (time.perf_counter() - start) * 1000
        if elapsed_ms >= SLOW_QUERY_THRESHOLD_MS:
            logger.warning("Slow query (%.1fms): %s", elapsed_ms, sql.strip()[:200])
        return result

    def cursor(self):
        return TimedCursor(self._connection.cursor())

    def commit(self):
        self._connection.commit()

    @property
    def row_factory(self):
        return self._connection.row_factory

    @row_factory.setter
    def row_factory(self, value):
        self._connection.row_factory = value


@contextmanager
def get_connection(db_path: str):
    """Context manager that yields a TimedConnection wrapping sqlite3.connect()."""
    with sqlite3.connect(db_path) as conn:
        yield TimedConnection(conn)


def validate_schema(db_path: str) -> list[str]:
    """
    Checks that all required tables and views exist in the database.

    Returns a list of missing object names. Empty list means everything is present.
    """
    missing = []
    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute(
            "SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view')"
        )
        existing = {row[0] for row in cursor.fetchall()}

    for table in REQUIRED_TABLES:
        if table not in existing:
            missing.append(f"table:{table}")
    for view in REQUIRED_VIEWS:
        if view not in existing:
            missing.append(f"view:{view}")
    return missing


def get_db_stats(db_path: str) -> dict:
    """
    Returns SQLite database statistics useful for monitoring.
    """
    stats = {}
    try:
        stats['file_size_mb'] = round(os.path.getsize(db_path) / (1024 * 1024), 2)
    except OSError:
        stats['file_size_mb'] = None

    wal_path = db_path + '-wal'
    try:
        stats['wal_size_mb'] = round(os.path.getsize(wal_path) / (1024 * 1024), 2)
    except OSError:
        stats['wal_size_mb'] = 0.0

    with sqlite3.connect(db_path) as connection:
        stats['page_size'] = connection.execute('PRAGMA page_size').fetchone()[0]
        stats['page_count'] = connection.execute('PRAGMA page_count').fetchone()[0]
        stats['freelist_count'] = connection.execute('PRAGMA freelist_count').fetchone()[0]
        stats['integrity_ok'] = connection.execute('PRAGMA quick_check(1)').fetchone()[0] == 'ok'

    return stats


def initialize_database(db_path: str):
    """
    Initializes the database by creating necessary tables.

    Parameters:
    - db_path: str
    """
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stocks (
                    stockid INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    symbol TEXT NOT NULL UNIQUE,
                    price REAL,
                    currency TEXT,
                    market_cap REAL,
                    sector TEXT,
                    industry TEXT,
                    country TEXT,
                    logo_url TEXT DEFAULT '',
                    quote_type TEXT DEFAULT 'EQUITY',
                    ex_dividend_date TEXT DEFAULT NULL
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS positions (
                    stockid INTEGER PRIMARY KEY,
                    quantity INTEGER,
                    average_cost_basis REAL,
                    distribution_target REAL,
                    distribution_real REAL,
                    FOREIGN KEY (stockid) REFERENCES stocks (stockid)
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS historicalstocks (
                    closeprice REAL    NULL    ,
                    stockid    INTEGER NOT NULL,
                    datestamp  TEXT    NULL    ,
                    FOREIGN KEY (stockid) REFERENCES stocks (stockid)
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
                    transactionid INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolioid   INTEGER NOT NULL,
                    rowid         INTEGER NOT NULL,
                    stockid       INTEGER NOT NULL,
                    quantity      INTEGER NULL    ,
                    price         REAL    NOT NULL,
                    type          TEXT    NULL    ,
                    datestamp     TEXT    NULL    ,
                    FOREIGN KEY (stockid) REFERENCES stocks (stockid)
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS historicaldividends (
                    datestamp     TEXT    NULL    ,
                    dividendvalue REAL    NULL    ,
                    stockid       INTEGER NOT NULL,
                    FOREIGN KEY (stockid) REFERENCES stocks (stockid)
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS deposits (
                    depositid   INTEGER PRIMARY KEY AUTOINCREMENT,
                    datestamp   TEXT    NULL    ,
                    amount      REAL   NOT NULL,
                    portfolioid INTEGER NOT NULL,
                    currency    TEXT    DEFAULT 'EUR'
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS net_worth_assets (
                    id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    current_value REAL NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS net_worth_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    asset_id TEXT NOT NULL,
                    value REAL NOT NULL,
                    FOREIGN KEY (asset_id) REFERENCES net_worth_assets (id),
                    UNIQUE(date, asset_id)
    )
    ''')
    connection.commit()

    # Migrate existing tables: add columns that may not exist yet
    _add_column_if_missing(cursor, 'stocks', 'logo_url', "TEXT DEFAULT ''")
    _add_column_if_missing(cursor, 'stocks', 'quote_type', "TEXT DEFAULT 'EQUITY'")
    _add_column_if_missing(cursor, 'stocks', 'ex_dividend_date', "TEXT DEFAULT NULL")

    # Recreate dbt-managed views to reflect new columns in stocks table
    _migrate_dbt_views(cursor)

    connection.commit()

    connection.close()


def _add_column_if_missing(cursor, table: str, column: str, column_def: str):
    """Add a column to a table if it doesn't already exist."""
    cursor.execute(f"PRAGMA table_info({table})")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if column not in existing_columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")
        logger.info("Added column %s to table %s", column, table)


def _migrate_dbt_views(cursor):
    """
    Recreate dbt-managed views so they reflect the current stocks table schema.
    Only runs if the views exist (i.e. dbt has been run at least once).
    """
    cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='core__stocks'")
    if not cursor.fetchone():
        return

    cursor.execute("DROP VIEW IF EXISTS mar__stocks")
    cursor.execute("DROP VIEW IF EXISTS core__stocks")

    cursor.execute('''
    CREATE VIEW IF NOT EXISTS core__stocks AS
    WITH
        stocks AS (SELECT * FROM stg__stocks),
        unlisted_stocks AS (SELECT * FROM stg__unlisted_stocks)
    SELECT * FROM stocks
    UNION ALL
    SELECT
        stockid, name, symbol,
        NULL AS price, NULL AS currency, NULL AS market_cap,
        NULL AS sector, NULL AS industry, NULL AS country,
        '' AS logo_url, 'EQUITY' AS quote_type,
        NULL AS ex_dividend_date
    FROM unlisted_stocks
    ''')

    cursor.execute('''
    CREATE VIEW IF NOT EXISTS mar__stocks AS
    WITH stocks AS (SELECT * FROM core__stocks)
    SELECT * FROM stocks
    ''')

    logger.info("Recreated core__stocks and mar__stocks views with updated schema")
