import sqlite3

def init_tables():
    connection = sqlite3.connect("data.db")
    cursor = connection.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stocks (
                    stockid INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    symbol TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS portfolio (
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
                    stockid       INTEGER NOT NULL,
                    quantity      INTEGER NULL    ,
                    price         REAL    NOT NULL,
                    type          TEXT    NULL    ,
                    datestamp     TEXT    NULL    ,
                    FOREIGN KEY (stockid) REFERENCES stocks (stockid)
    )
    ''')
    connection.commit()
    connection.close()