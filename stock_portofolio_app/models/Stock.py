from models.Base import BaseModel

class Stock(BaseModel):
    def create_table(self):
        self.execute_query('''
        CREATE TABLE IF NOT EXISTS stocks (
            stockid INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            name TEXT
        )
        ''')

    def add_stock(self, symbol, name):
        self.execute_query('INSERT INTO stocks (symbol, name) VALUES (?, ?)', (symbol, name))

    def get_stock(self, stockid):
        return self.execute_query('SELECT * FROM stocks WHERE stockid = ?', (stockid,))
