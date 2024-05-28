from numbers_parser import Document
from portfolio_balancer.stock import Stock
import pandas as pd
import sqlite3

def init_table():
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

def insert_stock(stock: Stock):
    with sqlite3.connect("data.db") as connection:
        cursor = connection.cursor()
        cursor.execute('''
        UPSERT INTO portfolio (symbol, quantity, distribution_target) VALUES (?, ?, ?)
        ''', (stock.symbol, stock.quantity, stock.distribution_target))
        connection.commit()


def load_numbers(filename: str):

    # Value to adapt 
    SHEET = 'Dividends'
    TABLE = 'Repartition'
    SYMBOL = 0
    QUANTITY = 2
    DISTRIBUTION_TARGET = -1
    
    try:
        doc = Document(filename)
    except Exception as e:
        raise e
    
    table = doc.sheets[SHEET].tables[TABLE]
    table.delete_row(num_rows=table.num_header_rows, start_row=0)

    with sqlite3.connect("data.db") as connection:
        cursor = connection.cursor()
        for row in table.rows(values_only=True):
            if row[0] is None:
                continue
            cursor.execute('''
                           INSERT INTO portfolio (symbol, quantity, distribution_target) VALUES (?, ?, ?)
                           ON CONFLICT(symbol) DO UPDATE SET quantity=excluded.quantity,  distribution_target=excluded. distribution_target 
            ''', (row[SYMBOL], int(row[QUANTITY]), row[DISTRIBUTION_TARGET]))

cursor = init_table()
portfolio = load_numbers("/Users/guillaumelongrais/Library/Mobile Documents/com~apple~Numbers/Documents/Investissement.numbers")

