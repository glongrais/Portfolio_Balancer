import datetime
from typing import Dict
import sqlite3
import logging
from models.Stock import Stock
from models.Position import Position
from services.data_processing import DataProcessing
from external.stock_api import StockAPI
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_PATH = '../data/portfolio.db'

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
        
        ticker_info = DataProcessing.fetch_real_time_price(symbol)
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute('''
            INSERT INTO stocks (symbol, name, price, currency, market_cap, sector, industry, country)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                name=excluded.name,
                price=excluded.price,
                currency=excluded.currency,
                market_cap=excluded.market_cap,
                sector=excluded.sector,
                industry=excluded.industry,
                country=excluded.country
            ''', (
                ticker_info["symbol"],
                ticker_info.get("longName", ""),
                ticker_info.get("currentPrice", None),
                ticker_info.get("currency", ""),
                ticker_info.get("marketCap", None),
                ticker_info.get("sector", ""),
                ticker_info.get("industry", ""),
                ticker_info.get("country", "")
            ))
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
                info = DataProcessing.fetch_real_time_price(stock.symbol)
                stock.price = info["currentPrice"]
                connection.execute('UPDATE stocks SET price = ? WHERE stockid = ?', (info["currentPrice"], stockid,))
                log_count += 1
            connection.commit()
        logger.info("updateStocksPrice(): Price updated for %d stock(s)", log_count)
    
    @classmethod
    def getStocks(cls) -> None:
        """
        Fetches all stocks from the database and updates the in-memory cache.
        """
        with sqlite3.connect(DB_PATH) as connection:
            connection.row_factory = Stock.dataclass_factory
            answers = connection.execute("SELECT * FROM mar__stocks")
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
                answers = connection.execute("SELECT * FROM mar__stocks WHERE stockid = ?", (stockid,))
            else:
                answers = connection.execute("SELECT * FROM mar__stocks WHERE symbol = ?", (symbol,))
        log_count = 0
        result = -1
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
        Updates the price of all the positions in the portfolio in parallel.
        """
        if not cls.positions:
            logger.warning("updatePortfolioPositionsPrice(): No position in the portfolio")
            return


        def update_single_position(position_data):
            stockid, position = position_data
            if position.stock is None:
                logger.warning("updatePortfolioPositionsPrice(): Position %d has no stock set. Skipping price update for this position", stockid)
                return None
            
            info = DataProcessing.fetch_real_time_price(position.stock.symbol)
            position.stock.price = info["currentPrice"]
            
            return (stockid, info)

        # Run price updates in parallel
        with ThreadPoolExecutor() as executor:
            future_to_position = {executor.submit(update_single_position, (stockid, position)): 
                                (stockid, position) for stockid, position in cls.positions.items()}
            
            # Update database with results
            with sqlite3.connect(DB_PATH) as connection:
                for future in as_completed(future_to_position):
                    result = future.result()
                    if result:
                        stockid, info = result
                        connection.execute(
                            "UPDATE stocks SET price=?,name=?,currency=?,market_cap=?,sector=?,industry=?,country=? WHERE stockid=?",
                            (info["currentPrice"], info["longName"], info["currency"], info["marketCap"],
                             info["sector"], info["industry"], info["country"], stockid,)
                        )
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
    def updatePosition(cls, symbol, quantity: int=None, average_cost_basis: float=None, distribution_target: float=None, distribution_real: float=None) -> None:
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
        if average_cost_basis is not None:
            position.average_cost_basis = average_cost_basis
            fields_to_update.append("average_cost_basis = ?")
            params.append(average_cost_basis)
        if not fields_to_update:
            logger.warning("updatePosition(): No fields to update for position %s", symbol)
            return

        params.append(stockid)
        query = "UPDATE positions SET " + ", ".join(fields_to_update) + " WHERE stockid = ?"

        with sqlite3.connect(DB_PATH) as connection:
            connection.execute(query, params)
            connection.commit()

        logger.debug(
            "updatePosition(): Position %s updated. Quantity: %s, Average cost basis: %s, Distribution target: %s, Distribution real: %s",
            symbol, position.quantity, position.average_cost_basis, position.distribution_target, position.distribution_real
        )
    
    @classmethod
    def upsertTransactions(cls, date: datetime, rowid: int, type: str, symbol: str, quantity: int, price: float) -> None:
        """
        Add or update a transaction in the database.

        :param date: The date of the transaction.
        :param type: The type of the transaction (buy or sell).
        :param symbol: The symbol of the stock in the transaction.
        :param quantity: The quantity of the stock in the transaction.
        :param price: The price of the stock in the transaction.
        """
        stockid = cls.getStock(symbol=symbol)
        if stockid == -1:
            stockid = cls.addStock(symbol)
            #logger.error("upsertTransactions(): Stock %s not in the database", symbol)
            #return
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute("INSERT INTO transactions (stockid, portfolioid, rowid, quantity, price, type, datestamp) VALUES (?, 1, ?, ?, ?, ?, ?) ON CONFLICT(portfolioid, rowid) DO NOTHING", (stockid, rowid, quantity, price, type, date,))
            connection.commit()
        logger.info("upsertTransactions(): Transaction added for stock %s", symbol)

    @classmethod
    def updateHistoricalStocksPortfolio(cls, start_date: str, end_date: str) -> None:
        """
        Updates the historicalstocks table with data fetched from the StockAPI.

        :param start_date: Start date for the historical data (YYYY-MM-DD).
        :param end_date: End date for the historical data (YYYY-MM-DD).
        """
        symbols = [p.stock.symbol for p in cls.positions.values()]

        # Fetch the last timestamp from the table
        with sqlite3.connect(DB_PATH) as connection:
            answers = connection.execute('SELECT MAX(datestamp) FROM historicalstocks')
            last_timestamp = answers.fetchone()[0]

        historical_data = StockAPI.get_historical_data(symbols, last_timestamp)

        with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.cursor()
            for stock_data in historical_data:
                for _, row in stock_data.iterrows():
                    stockid = cls.symbol_map.get(row['Ticker'])
                    if stockid is None:
                        logger.warning("updateHistoricalStocks(): Stock %s not found in symbol_map. Skipping.", row['Ticker'])
                        continue
                    cursor.execute('''
                    INSERT INTO historicalstocks (closeprice, stockid, datestamp)
                    VALUES (?, ?, ?)
                    ON CONFLICT(stockid, datestamp) DO UPDATE SET
                        closeprice = excluded.closeprice
                    ''', (row['Close'], stockid, row['Date'].strftime('%Y-%m-%d')))
            connection.commit()
        logger.info("updateHistoricalStocks(): Historical data updated for %d symbol(s)", len(symbols))
    
    @classmethod
    def updateHistoricalDividendsPortfolio(cls) -> None:
        """
        Updates the historicaldividends table with data fetched from the StockAPI.

        :param symbols: List of stock symbols to fetch historical dividends for.
        """

        symbols = [p.stock.symbol for p in cls.positions.values()]
        historical_dividends = DataProcessing.fetch_historical_dividends(symbols)

        with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.cursor()
            for symbol, dividends in historical_dividends.items():
                stockid = cls.symbol_map.get(symbol)
                if stockid is None:
                    logger.warning("updateHistoricalDividends(): Stock %s not found in symbol_map. Skipping.", symbol)
                    continue
                for date, dividend in dividends.items():
                    cursor.execute('''
                    INSERT INTO historicaldividends (dividendvalue, stockid, datestamp)
                    VALUES (?, ?, ?)
                    ON CONFLICT(stockid, datestamp) DO UPDATE SET
                        dividendvalue = excluded.dividendvalue
                    ''', (dividend, stockid, date))
            connection.commit()
        logger.info("updateHistoricalDividends(): Historical dividends updated for %d symbol(s)", len(symbols))

    @classmethod
    def getPortfolioValueHistory(cls) -> list:
        """
        Retrieves the portfolio value history.

        Returns:
        - list: Portfolio value history
        """
        with sqlite3.connect(DB_PATH) as connection:
            answers = connection.execute("SELECT * FROM int__portfolio_value_evolution")
        return answers
    
    @classmethod
    def getDividendTotal(cls) -> float:
        """
        Calculates the total yearly dividend for the portfolio.

        Returns:
        - float: Total yearly dividend
        """
        total_dividend = 0.0
        with sqlite3.connect(DB_PATH) as connection:
            answers = connection.execute('''SELECT * FROM int__portfolio_dividends_total''')
            total_dividend = float(answers.fetchone()[0])
        return round(total_dividend, 2)

    @classmethod
    def getDividendYearToDate(cls, year: str) -> float:
        """
        Calculates the total dividends received for a given year.

        Args:
        - year: The year to calculate dividends for (e.g., '2024')

        Returns:
        - float: Total dividends for the year
        """
        with sqlite3.connect(DB_PATH) as connection:
            result = connection.execute(
                '''SELECT SUM(total_dividends) 
                   FROM int__transactions_dividends 
                   WHERE strftime('%Y', datestamp) = ?''',
                (year,)
            )
            row = result.fetchone()
            return round(row[0], 2) if row[0] else 0.0

    @classmethod
    def getNextDividendInfo(cls) -> dict:
        """
        Retrieves information about the most recent dividend to estimate next payment.

        Returns:
        - dict: Contains stockid and dividend_rate (never returns None)
        """
        default_result = {'stockid': None, 'dividend_rate': 0.0}
        try:
            with sqlite3.connect(DB_PATH) as connection:
                result = connection.execute(
                    '''SELECT stockid, MAX(datestamp) as last_date, dividendvalue
                       FROM historicaldividends
                       GROUP BY stockid
                       ORDER BY last_date DESC
                       LIMIT 1'''
                )
                row = result.fetchone()
                if row and row[0] is not None:
                    return {
                        'stockid': row[0],
                        'dividend_rate': row[2] if row[2] else 0.0
                    }
        except Exception as e:
            logger.error(f"getNextDividendInfo(): Error fetching next dividend info: {e}")
        return default_result