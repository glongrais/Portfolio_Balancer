from typing import Dict
import sqlite3
from models.Stock import Stock

class DatabaseService:

    stocks: Dict[int, Stock] = {}

    @classmethod
    def addStock(cls):
        return
    
    @classmethod
    def getStocks(cls):
        with sqlite3.connect('data/portfolio.db') as connection:
            connection.row_factory = Stock.dataclass_factory
            answers = connection.execute("SELECT * FROM stocks")
        for answer in answers:
            cls.stocks[answer.stockid] = answer