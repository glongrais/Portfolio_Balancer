from typing import Dict
import sqlite3
import logging
from models.Stock import Stock
from models.Portfolio import Portfolio
from services.data_processing import DataProcessing

DB_PATH = 'data/portfolio.db'

logger = logging.getLogger(__name__)

class DatabaseService:

    symbol_map: Dict[str, int] = {}
    stocks: Dict[int, Stock] = {}
    portfolio: Dict[int, Portfolio] = {}

    @classmethod
    def addStock(cls, symbol):
        """
        Adds a new stock to the database if it does not already exist.

        :param symbol: The stock symbol to be added.
        """
        if symbol in cls.symbol_map:
            logger.info("addStock(): Stock %s already in the database", symbol)
            return
        price = DataProcessing.fetch_real_time_price(symbol)
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute('INSERT INTO stocks (symbol, price) VALUES (?, ?)', (symbol,price,))
            connection.commit()
        cls.getStock(symbol=symbol)
        logger.info("addStock(): %s added in the database", symbol)
    
    @classmethod
    def updateStocksPrice(cls):
        """
        Updates all stocks price in the database and in the in-memory cache
        """
        with sqlite3.connect(DB_PATH) as connection:
            log_count = 0
            for stockid in cls.stocks:
                stock = cls.stocks[stockid]
                price = DataProcessing.fetch_real_time_price(stock.symbol)
                stock.price = price
                connection.execute('UPDATE stocks SET price = ? WHERE stockid = ?', (price, stockid,))
                log_count += 1
            connection.commit()
        logger.info("addStock(): Price updated for %d stock(s)", log_count)
    
    @classmethod
    def getStocks(cls) -> None:
        """
        Fetches all stocks from the database and updates the in-memory cache.
        """
        with sqlite3.connect(DB_PATH) as connection:
            connection.row_factory = Stock.dataclass_factory
            answers = connection.execute("SELECT * FROM stocks")
        log_count = 0
        for answer in answers:
            cls.stocks[answer.stockid] = answer
            cls.symbol_map[answer.symbol] = answer.stockid
            log_count += 1
        logger.info("getStocks(): %d stock(s) fetched from the database", log_count)

    @classmethod
    def getStock(cls, stockid=None, symbol=None) -> None:
        """
        Fetches a specific stock by its ID or symbol and updates the in-memory cache.

        :param stockid: The stock ID to search for (default is None).
        :param symbol: The stock symbol to search for (default is None).
        """
        if stockid is None and symbol is None:
            logger.error("getStock(): At least one parameter (stockid or symbol) must be set.")
            return
        if stockid is not None and symbol is not None:
            logger.warning("getStock(): Both stockid and symbol are set; the search will be done using stockid.")
        with sqlite3.connect(DB_PATH) as connection:
            connection.row_factory = Stock.dataclass_factory
            if stockid is not None:
                answers = connection.execute("SELECT * FROM stocks WHERE stockid = ?", (stockid,))
            else:
                answers = connection.execute("SELECT * FROM stocks WHERE symbol = ?", (symbol,))
        for answer in answers:
            cls.stocks[answer.stockid] = answer
            cls.symbol_map[answer.symbol] = answer.stockid
    
    @classmethod
    def getPortfolio(cls):
        """
        Fetches all portfolio positions from the database and updates the in-memory cache.
        """
        with sqlite3.connect(DB_PATH) as connection:
            connection.row_factory = Portfolio.dataclass_factory
            answers = connection.execute("SELECT * FROM portfolio")
        log_count = 0  
        for answer in answers:
            cls.portfolio[answer.stockid] = answer
            log_count += 1
        logger.info("getPortfolio(): %d portfolio position(s) fetched from the database", log_count)