from numbers_parser import Document
from portfolio_balancer.stock import Stock

def load_numbers(filename: str) -> list[Stock]:

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