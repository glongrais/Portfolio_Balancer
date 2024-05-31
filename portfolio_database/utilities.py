import sqlite3

def init_tables():
    connection = sqlite3.connect("data.db")
    cursor = connection.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS portfolio (
                   symbol TEXT PRIMARY KEY,
                   name TEXT,
                   price FLOAT,
                   quantity INTEGER,
                   distribution_target FLOAT,
                   distribution_real FLOAT

    )
    ''')
    connection.commit()
    connection.close()