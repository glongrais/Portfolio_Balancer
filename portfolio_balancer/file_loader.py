from portfolio_balancer.stock import Stock
from portfolio_balancer.exception import UnsupportedFileTypeError
import os
from numbers_parser import Document, EmptyCell
import json

def load_file(filename: str) -> list[Stock]:
    try:
        if filename.lower().endswith('.json'):
            return _load_json(filename)
        elif filename.lower().endswith('.numbers'):
            return _load_numbers(filename)
        else:
            _, file_extension = os.path.splitext(filename)
            raise UnsupportedFileTypeError(file_extension)
    except UnsupportedFileTypeError as e:
        raise e

def _load_json(filename: str) -> list[Stock]:
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"The file {filename} was not found.") from e
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Error decoding JSON from the file {filename}.", e.doc, e.pos)

    return [Stock(**i) for i in data]

def _load_numbers(filename: str) -> list[Stock]:

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

    data = []
    for row in table.rows(values_only=True):
        if row[0] is None:
            continue
        data.append(Stock(symbol=row[SYMBOL], quantity=int(row[QUANTITY]), distribution_target=row[DISTRIBUTION_TARGET]*100))

    return data