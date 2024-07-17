from numbers_parser import Document
from models.Stock import Stock
from models.Portfolio import Portfolio

class fileUtils:

    @classmethod
    def load_numbers(filename: str):

        # Value to adapt 
        SHEET = 'Dividends'
        TABLE = 'Repartition'
        SYMBOL = 0
        QUANTITY = 2
        DISTRIBUTION_TARGET = -1

        stock = Stock()
        portfolio = Portfolio()
        
        try:
            doc = Document(filename)
        except Exception as e:
            raise e
        
        table = doc.sheets[SHEET].tables[TABLE]
        table.delete_row(num_rows=table.num_header_rows, start_row=0)

        for row in table.rows(values_only=True):
            if row[0] is None:
                continue
            stockid = stock.get_sotckid_from_symbol(row[SYMBOL])
            if stockid == None:
                stock.add_stock(row[SYMBOL])
                stockid = stock.get_sotckid_from_symbol(row[SYMBOL])
            portfolio.add_to_portfolio(stockid, int(row[QUANTITY]), row[DISTRIBUTION_TARGET]*100)