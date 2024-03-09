from stock import Stock
import json

def load_file(filename: str) -> list[Stock]:
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"The file {filename} was not found.") from e
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Error decoding JSON from the file {filename}.", e.doc, e.pos)

    return [Stock(**i) for i in data]