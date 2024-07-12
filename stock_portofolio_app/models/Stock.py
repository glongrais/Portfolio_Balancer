from models.Base import BaseModel
from services.data_processing import DataProcessing
from dataclasses import dataclass, field

""" class Stock(BaseModel):

    def __init__(self, db_path='data/portfolio.db'):
        super().__init__('stocks', db_path)
        self.create_table()

    def create_table(self):
        self.execute_query('''
        CREATE TABLE IF NOT EXISTS stocks (
            stockid INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            name TEXT,
            price REAL
        )
        ''')

    def add_stock(self, symbol):
        price = DataProcessing.fetch_real_time_price(symbol)
        self.execute_query('INSERT INTO stocks (symbol, price) VALUES (?, ?)', (symbol,price,))

    def get_stock(self, stockid):
        return self.execute_query('SELECT * FROM stocks WHERE stockid = ?', (stockid,))[0]
    
    def get_sotckid_from_symbol(self, symbol):
        result = self.execute_query('SELECT stockid FROM stocks WHERE symbol = ?', (symbol,))
        if len(result) == 0:
            return None
        else:
            return result[0][0]
    
    def update_prices(self):
        symbols = self.execute_query('SELECT symbol FROM stocks')

        for symbol in symbols:
            price = DataProcessing.fetch_real_time_price(symbol[0])
            self.execute_query('UPDATE stocks SET price = ? WHERE symbol = ?', (price, symbol[0],)) """

@dataclass
class Stock:
    stockid: int
    symbol: str
    name: str = field(default="")
    price: float = field(default=0.0)

    @classmethod
    def dataclass_factory(cls, cursor, row):
        fields = [column[0] for column in cursor.description]
        return Stock(**{k: v for k, v in zip(fields, row)})
