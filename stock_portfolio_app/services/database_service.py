from typing import Dict
import sqlite3
import logging
from models.Stock import Stock
from models.Position import Position
from services.data_processing import DataProcessing

DB_PATH = 'data/portfolio.db'

logger = logging.getLogger(__name__)

class DatabaseService:

    symbol_map: Dict[str, int] = {}
    stocks: Dict[int, Stock] = {}
    positions: Dict[int, Position] = {}

    @classmethod
    def addStock(cls, symbol) -> int:
        """
        Adds a new stock to the database if it does not already exist.

        :param symbol: The stock symbol to be added.
        :return: The stockid of the stock added. Also return stockid if the stock is already in the database
        """
        if symbol in cls.symbol_map:
            logger.warning("addStock(): Stock %s already in the database", symbol)
            return cls.symbol_map[symbol]
        price = DataProcessing.fetch_real_time_price(symbol)
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute('INSERT INTO stocks (symbol, price) VALUES (?, ?)', (symbol,price,))
            connection.commit()
        stockid = cls.getStock(symbol=symbol)
        logger.info("addStock(): %s added in the database", symbol)
        return stockid
    
    @classmethod
    def updateStocksPrice(cls) -> None:
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
    def getStock(cls, stockid=None, symbol=None) -> int:
        """
        Fetches a specific stock by its ID or symbol and updates the in-memory cache.

        :param stockid: The stock ID to search for (default is None).
        :param symbol: The stock symbol to search for (default is None).
        :return: The stockid if the stock was found and updated in the cache, -1 otherwise.
        """
        if stockid is None and symbol is None:
            logger.error("getStock(): At least one parameter (stockid or symbol) must be set.")
            return -1
        if stockid is not None and symbol is not None:
            logger.warning("getStock(): Both stockid and symbol are set; the search will be done using stockid.")
        with sqlite3.connect(DB_PATH) as connection:
            connection.row_factory = Stock.dataclass_factory
            if stockid is not None:
                answers = connection.execute("SELECT * FROM stocks WHERE stockid = ?", (stockid,))
            else:
                answers = connection.execute("SELECT * FROM stocks WHERE symbol = ?", (symbol,))
        log_count = 0
        for answer in answers:
            cls.stocks[answer.stockid] = answer
            cls.symbol_map[answer.symbol] = answer.stockid
            result = answer.stockid
            log_count +=1
        if log_count == 0:
            if stockid is not None:
                logger.warning("getStock(): Stock with stockid %d not in databse", stockid)
            else:
                logger.warning("getStock(): Stock with symbol %s not in databse", symbol)
            return -1
        return result
    
    @classmethod
    def updatePortfolioPositionsPrice(cls) -> None:
        """
        Updates the price of all the positions in the portfolio, both in the database and in the in-memory cahce
        """
        if not cls.positions:
            logger.warning("updatePortfolioPositionsPrice(): No position in the portfolio")
            return
        for stockid in cls.positions:
            position = cls.positions[stockid]
            if position.stock is None:
                logger.warning("updatePortfolioPositionsPrice(): Position %d has no stock set. Skipping price update for this position", stockid)
                continue
            new_price = DataProcessing.fetch_real_time_price(position.stock.symbol)
            position.stock.price = new_price
            with sqlite3.connect(DB_PATH) as connection:
                connection.execute("UPDATE stocks SET price=? WHERE stockid=?", (new_price,stockid,))
                connection.commit()
    
    @classmethod
    def getPositions(cls) -> None:
        """
        Fetches all portfolio positions from the database and updates the in-memory cache.
        """
        with sqlite3.connect(DB_PATH) as connection:
            connection.row_factory = Position.dataclass_factory
            answers = connection.execute("SELECT * FROM positions")
        log_count = 0  
        for answer in answers:
            if answer.stockid not in cls.stocks:
                if cls.getStock(stockid=answer.stockid) > -1:
                    answer.stock = cls.stocks[answer.stockid]
                else:
                    logger.error("getPosition(): Stock with id %d not in the database", answer.stockid)
            else:
                answer.stock = cls.stocks[answer.stockid]
            cls.positions[answer.stockid] = answer
            log_count += 1
        logger.info("getPosition(): %d portfolio position(s) fetched from the database", log_count)
    
    @classmethod
    def addPosition(cls, symbol, quantity: int, distribution_target: float=None) -> None:
        """
        Add a new position in the portfolio database and in-memory cache.

        :param symbol: The symbol of the stock in the position
        """
        stockid = cls.addStock(symbol=symbol)

        if stockid in cls.positions:
            logger.warning("addPosition(): Position %s already in the portfolio", symbol)
            return
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute("INSERT INTO positions (stockid, quantity, distribution_target) VALUES (?, ?, ?)", (stockid, quantity, distribution_target))
            connection.commit()
        cls.positions[stockid] = Position(stockid=stockid, quantity=quantity, distribution_target=distribution_target, stock=cls.stocks[stockid])
        logger.info("addPosition(): Added position %s to the portfolio", symbol)

    @classmethod
    def updatePosition(cls, symbol, quantity: int=None, distribution_target: float=None, distribution_real: float=None) -> None:
        """
        Update an existing position in the portfolio database and in-memory cache.
        
        :param symbol: The stock symbol of the position to update.
        :param quantity: The new quantity of the position (default is None).
        :param distribution_target: The new target distribution of the position (default is None).
        :param distribution_real: The new real distribution of the position (default is None).
        """
        if symbol not in cls.symbol_map:
            logger.warning("updatePosition(): Position %s not in the portfolio", symbol)
            return

        stockid = cls.symbol_map[symbol]
        if stockid not in cls.positions:
            logger.warning("updatePosition(): Position %s not in the portfolio", symbol)
            return

        position = cls.positions[stockid]
        fields_to_update = []
        params = []

        if quantity is not None:
            position.quantity = quantity
            fields_to_update.append("quantity = ?")
            params.append(quantity)
        if distribution_target is not None:
            position.distribution_target = distribution_target
            fields_to_update.append("distribution_target = ?")
            params.append(distribution_target)
        if distribution_real is not None:
            position.distribution_real = distribution_real
            fields_to_update.append("distribution_real = ?")
            params.append(distribution_real)

        if not fields_to_update:
            logger.warning("updatePosition(): No fields to update for position %s", symbol)
            return

        params.append(stockid)
        query = "UPDATE positions SET " + ", ".join(fields_to_update) + " WHERE stockid = ?"

        with sqlite3.connect(DB_PATH) as connection:
            connection.execute(query, params)
            connection.commit()

        logger.info(
            "updatePosition(): Position %s updated. Quantity: %s, Distribution target: %s, Distribution real: %s",
            symbol, position.quantity, position.distribution_target, position.distribution_real
        )
