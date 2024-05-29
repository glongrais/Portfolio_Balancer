from portfolio_balancer.stock import Stock
from portfolio_balancer.exception import UnsupportedFileTypeError
import os
import json
from portfolio_balancer.stock import Stock

import sqlite3

def load_database() -> list[Stock]:

    with sqlite3.connect("data.db") as connection:
        cursor = connection.cursor()
        cursor.execute('''
            SELECT symbol, quantity, distribution_target FROM portfolio
                       ''')
        rows = cursor.fetchall()
    data = []
    for row in rows:
        data.append(Stock(symbol=row[0], quantity=int(row[1]), distribution_target=row[2]*100))

    return data

def load_json(filename: str) -> list[Stock]:
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"The file {filename} was not found.") from e
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Error decoding JSON from the file {filename}.", e.doc, e.pos)

    return [Stock(**i) for i in data]

class FileLoader:

    @staticmethod
    def load_file(filename: str) -> list[Stock]:
        try:
            if filename.lower().endswith('.json'):
                return load_json(filename)
            elif filename == 'No file':
                return load_database()
            else:
                _, file_extension = os.path.splitext(filename)
                raise UnsupportedFileTypeError(file_extension)
        except UnsupportedFileTypeError as e:
            raise e