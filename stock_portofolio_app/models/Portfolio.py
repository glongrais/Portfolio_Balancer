from models.Base import BaseModel
from enum import Enum

class Portfolio(BaseModel):

    class Field(Enum):
        STOCKID = 'stockid'
        QUANTITY = 'quantity'
        DISTRIBUTIONTARGET = 'distribution_target'
        DISTRIBUTIONREAL = 'distribution_real'
    
    def __init__(self, db_path='data/portfolio.db'):
        super().__init__('portfolio', db_path)
        self.create_table()

    def create_table(self):
        self.execute_query('''
        CREATE TABLE IF NOT EXISTS portfolio (
            stockid INTEGER,
            quantity INTEGER NOT NULL,
            distribution_target REAL,
            distribution_real REAL,
            FOREIGN KEY (stockid) REFERENCES stocks(stockid)
        )
        ''')

    def add_to_portfolio(self, stockid, quantity, distribution_target):
        self.execute_query('''
        INSERT INTO portfolio (stockid, quantity, distribution_target)
        VALUES (?, ?, ?)
        ''', (stockid, quantity, distribution_target))

    def update_field(self, stockid, value, field: Field):
        self.execute_query('''
        UPDATE portfolio SET ? = ?
        WHERE stockid = ?
        ''', (field, value, stockid))
