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
    connection.commit()
    connection.close()

def store_ticker_info(db_path: str, ticker_info: dict):
    """
    Stores detailed ticker information in the database.

    Parameters:
    - db_path: str
    - ticker_info: dict
    """
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # Insert or update stock information
    cursor.execute('''
    INSERT INTO stocks (name, symbol, price, currency, market_cap, sector, industry, country)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(symbol) DO UPDATE SET
        name=excluded.name,
        price=excluded.price,
        currency=excluded.currency,
        market_cap=excluded.market_cap,
        sector=excluded.sector,
        industry=excluded.industry,
        country=excluded.country
    ''', (
        ticker_info.get("longName", ""),
        ticker_info["symbol"],
        ticker_info.get("currentPrice", None),
        ticker_info.get("currency", ""),
        ticker_info.get("marketCap", None),
        ticker_info.get("sector", ""),
        ticker_info.get("industry", ""),
        ticker_info.get("country", "")
    ))

    # Commit and close connection
    connection.commit()
    connection.close()