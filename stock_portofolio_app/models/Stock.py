from models.Base import BaseModel

class Stock(BaseModel):

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
        self.execute_query('INSERT INTO stocks symbol VALUES ?', (symbol))

    def get_stock(self, stockid):
        return self.execute_query('SELECT * FROM stocks WHERE stockid = ?', (stockid,))
