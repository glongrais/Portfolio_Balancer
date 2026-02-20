import sqlite3

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
                    country TEXT
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
    connection.commit()
    connection.close()
