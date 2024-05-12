from portfolio_balancer.stock import Stock
from portfolio_balancer.exception import UnsupportedFileTypeError
from portfolio_balancer.file_loader_numbers import load_numbers
import os
import json

def load_file(filename: str) -> list[Stock]:
    try:
        if filename.lower().endswith('.json'):
            return _load_json(filename)
        elif filename == 'No file':
            return load_numbers()
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