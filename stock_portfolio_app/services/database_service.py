import datetime
from typing import Dict
import sqlite3
import logging
from models.Stock import Stock
from models.Position import Position
from services.stock_api import StockAPI
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import DB_PATH
from utils.db_utils import get_connection

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
        
        ticker_info = StockAPI.get_current_price(symbol)
        with get_connection(DB_PATH) as connection:
            connection.execute('''
            INSERT INTO stocks (symbol, name, price, currency, market_cap, sector, industry, country, ex_dividend_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                name=excluded.name,
                price=excluded.price,
                currency=excluded.currency,
                market_cap=excluded.market_cap,
                sector=excluded.sector,
                industry=excluded.industry,
                country=excluded.country,
                ex_dividend_date=excluded.ex_dividend_date
            ''', (
                ticker_info["symbol"],
                ticker_info.get("longName", ""),
                ticker_info.get("currentPrice", None),
                ticker_info.get("currency", ""),
                ticker_info.get("marketCap", None),
                ticker_info.get("sector", ""),
                ticker_info.get("industry", ""),
                ticker_info.get("country", ""),
                ticker_info.get("exDividendDate"),
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
        with get_connection(DB_PATH) as connection:
            log_count = 0
            for stockid in cls.stocks:
                stock = cls.stocks[stockid]
                info = StockAPI.get_current_price(stock.symbol)
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
        with get_connection(DB_PATH) as connection:
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
        with get_connection(DB_PATH) as connection:
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
            
            info = StockAPI.get_current_price(position.stock.symbol)
            position.stock.price = info["currentPrice"]
            position.stock.logo_url = info.get("logo_url", "")
            position.stock.quote_type = info.get("quoteType", "EQUITY")
            position.stock.ex_dividend_date = info.get("exDividendDate")

            return (stockid, info)

        # Run price updates in parallel
        with ThreadPoolExecutor() as executor:
            future_to_position = {executor.submit(update_single_position, (stockid, position)): 
                                (stockid, position) for stockid, position in cls.positions.items()}
            
            # Update database with results
            with get_connection(DB_PATH) as connection:
                for future in as_completed(future_to_position):
                    result = future.result()
                    if result:
                        stockid, info = result
                        connection.execute(
                            "UPDATE stocks SET price=?,name=?,currency=?,market_cap=?,sector=?,industry=?,country=?,logo_url=?,quote_type=?,ex_dividend_date=? WHERE stockid=?",
                            (info["currentPrice"], info["longName"], info["currency"], info["marketCap"],
                             info["sector"], info["industry"], info["country"],
                             info.get("logo_url", ""), info.get("quoteType", "EQUITY"),
                             info.get("exDividendDate"), stockid,)
                        )
                connection.commit()
    
    @classmethod
    def getPositions(cls) -> None:
        """
        Fetches all portfolio positions from the database and updates the in-memory cache.
        """
        with get_connection(DB_PATH) as connection:
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
        with get_connection(DB_PATH) as connection:
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

        with get_connection(DB_PATH) as connection:
            connection.execute(query, params)
            connection.commit()

        logger.debug(
            "updatePosition(): Position %s updated. Quantity: %s, Average cost basis: %s, Distribution target: %s, Distribution real: %s",
            symbol, position.quantity, position.average_cost_basis, position.distribution_target, position.distribution_real
        )

    @classmethod
    def removePosition(cls, symbol: str) -> None:
        """
        Remove a position from the portfolio. Requires quantity to be 0.
        Stock record and transaction history are preserved.

        :param symbol: The stock symbol of the position to remove.
        :raises KeyError: If the stock or position is not found.
        :raises ValueError: If the position still has shares.
        """
        if symbol not in cls.symbol_map:
            raise KeyError(f"Stock with symbol '{symbol}' not found")

        stockid = cls.symbol_map[symbol]
        if stockid not in cls.positions:
            raise KeyError(f"Position for '{symbol}' not found")

        current_qty = cls.positions[stockid].quantity
        if current_qty != 0:
            raise ValueError(
                f"Cannot remove position '{symbol}': quantity is {current_qty}. Sell all shares first."
            )

        with get_connection(DB_PATH) as connection:
            connection.execute("DELETE FROM positions WHERE stockid = ?", (stockid,))
            connection.commit()

        del cls.positions[stockid]
        logger.info("removePosition(): Removed position %s from the portfolio", symbol)

    @classmethod
    def upsertTransactions(cls, date: datetime, rowid: int, type: str, symbol: str, quantity: int, price: float) -> None:
        """
        Add or update a transaction in the database.
        For buy/sell transactions, automatically updates position quantity if the position exists.

        :param date: The date of the transaction.
        :param type: The type of the transaction (buy or sell).
        :param symbol: The symbol of the stock in the transaction.
        :param quantity: The quantity of the stock in the transaction.
        :param price: The price of the stock in the transaction.
        :raises ValueError: If selling more shares than currently held.
        """
        stockid = cls.getStock(symbol=symbol)
        if stockid == -1:
            stockid = cls.addStock(symbol)

        # Validate sell quantity before inserting the transaction
        if type == 'sell' and stockid in cls.positions:
            current_qty = cls.positions[stockid].quantity
            if quantity > current_qty:
                raise ValueError(
                    f"Cannot sell {quantity} shares of {symbol}: only {current_qty} shares held"
                )

        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "INSERT INTO transactions (stockid, portfolioid, rowid, quantity, price, type, datestamp) "
                "VALUES (?, 1, ?, ?, ?, ?, ?) ON CONFLICT(portfolioid, rowid) DO NOTHING",
                (stockid, rowid, quantity, price, type, date,)
            )
            connection.commit()
            rows_inserted = cursor.rowcount

        logger.info("upsertTransactions(): Transaction added for stock %s", symbol)

        # Auto-update position quantity if a row was actually inserted
        if rows_inserted > 0 and stockid in cls.positions:
            old_qty = cls.positions[stockid].quantity
            if type == 'sell':
                new_qty = old_qty - quantity
                cls.updatePosition(symbol, quantity=new_qty)
                logger.info(
                    "upsertTransactions(): Sold %d shares of %s. Position quantity: %d -> %d",
                    quantity, symbol, old_qty, new_qty
                )
            elif type == 'buy':
                new_qty = old_qty + quantity
                cls.updatePosition(symbol, quantity=new_qty)
                logger.info(
                    "upsertTransactions(): Bought %d shares of %s. Position quantity: %d -> %d",
                    quantity, symbol, old_qty, new_qty
                )

    @classmethod
    def getTransactions(cls, symbol: str = None, transaction_type: str = None, limit: int = 100) -> list:
        """
        Fetches transaction history from the database with optional filtering.

        :param symbol: Filter by stock symbol (optional).
        :param transaction_type: Filter by transaction type - buy/sell (optional).
        :param limit: Maximum number of transactions to return.
        :return: List of transaction dicts.
        """
        query = ("SELECT t.transactionid, t.stockid, s.symbol, t.quantity, t.price, t.type, t.datestamp, s.name "
                 "FROM transactions t JOIN stocks s ON t.stockid = s.stockid")
        params = []
        conditions = []

        if symbol:
            conditions.append("s.symbol = ?")
            params.append(symbol.upper())

        if transaction_type:
            conditions.append("t.type = ?")
            params.append(transaction_type.lower())

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY t.datestamp DESC LIMIT ?"
        params.append(limit)

        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(query, params)
            rows = cursor.fetchall()

        return [
            {
                "transactionid": row[0],
                "stockid": row[1],
                "symbol": row[2],
                "quantity": row[3],
                "price": row[4],
                "type": row[5],
                "datestamp": row[6],
                "name": row[7],
            }
            for row in rows
        ]

    @classmethod
    def getTransactionSummary(cls, symbol: str = None) -> list:
        """
        Gets transaction summary statistics, optionally filtered by symbol.

        :param symbol: Filter by stock symbol (optional).
        :return: List of summary dicts per stock.
        """
        query = """
            SELECT
                s.symbol,
                s.name,
                COUNT(*) as transaction_count,
                SUM(CASE WHEN t.type = 'buy' THEN t.quantity ELSE 0 END) as total_bought,
                SUM(CASE WHEN t.type = 'sell' THEN t.quantity ELSE 0 END) as total_sold,
                SUM(CASE WHEN t.type = 'buy' THEN t.quantity * t.price ELSE 0 END) as total_invested,
                SUM(CASE WHEN t.type = 'sell' THEN t.quantity * t.price ELSE 0 END) as total_divested
            FROM transactions t
            JOIN stocks s ON t.stockid = s.stockid
        """
        params = []

        if symbol:
            query += " WHERE s.symbol = ?"
            params.append(symbol.upper())

        query += " GROUP BY s.symbol, s.name ORDER BY total_invested DESC"

        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(query, params)
            rows = cursor.fetchall()

        return [
            {
                "symbol": row[0],
                "name": row[1],
                "transaction_count": row[2],
                "total_bought": row[3],
                "total_sold": row[4],
                "total_invested": round(row[5], 2),
                "total_divested": round(row[6], 2),
                "net_shares": row[3] - row[4],
                "net_investment": round(row[5] - row[6], 2),
            }
            for row in rows
        ]

    @classmethod
    def getDeposits(cls, limit: int = 100) -> list:
        """
        Fetches deposit history from the database.

        :param limit: Maximum number of deposits to return.
        :return: List of deposit dicts.
        """
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "SELECT depositid, datestamp, amount, portfolioid, currency FROM deposits ORDER BY datestamp DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
        return [
            {
                "depositid": row[0],
                "datestamp": row[1],
                "amount": row[2],
                "portfolioid": row[3],
                "currency": row[4] or "EUR",
            }
            for row in rows
        ]

    @classmethod
    def getTotalDeposits(cls) -> float:
        """
        Calculates the total amount deposited.

        :return: Total deposit amount.
        """
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute("SELECT COALESCE(SUM(amount), 0) FROM deposits")
            total = cursor.fetchone()[0]
        return round(total, 2)

    @classmethod
    def addDeposit(cls, datestamp: str, amount: float) -> dict:
        """
        Adds a new deposit to the database.

        :param datestamp: The deposit date (YYYY-MM-DD string).
        :param amount: The deposit amount.
        :return: Dict with the created deposit data.
        """
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "INSERT INTO deposits (datestamp, amount, portfolioid, currency) VALUES (?, ?, 1, 'EUR')",
                (datestamp, amount)
            )
            connection.commit()
            deposit_id = cursor.lastrowid
        return {
            "depositid": deposit_id,
            "datestamp": datestamp,
            "amount": amount,
            "portfolioid": 1,
            "currency": "EUR",
        }

    @classmethod
    def getNetWorthAssets(cls) -> list:
        """
        Fetches all net worth asset categories from the database.

        :return: List of asset dicts with id, label, current_value, updated_at.
        """
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "SELECT id, label, current_value, updated_at FROM net_worth_assets ORDER BY id ASC"
            )
            rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "label": row[1],
                "current_value": row[2],
                "updated_at": row[3],
            }
            for row in rows
        ]

    @classmethod
    def addNetWorthAsset(cls, id: str, label: str, current_value: float) -> dict:
        """
        Adds a new net worth asset category.

        :param id: Slug identifier (e.g. 'cto', 'crypto').
        :param label: Display name.
        :param current_value: Current value in EUR.
        :return: Dict with the created asset data.
        :raises ValueError: If an asset with this id already exists.
        """
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        try:
            with get_connection(DB_PATH) as connection:
                connection.execute(
                    "INSERT INTO net_worth_assets (id, label, current_value, updated_at) VALUES (?, ?, ?, ?)",
                    (id, label, current_value, today)
                )
                connection.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"Asset with id '{id}' already exists")
        return {
            "id": id,
            "label": label,
            "current_value": current_value,
            "updated_at": today,
        }

    @classmethod
    def updateNetWorthAsset(cls, id: str, label: str = None, current_value: float = None) -> dict:
        """
        Updates an existing net worth asset category.

        :param id: The asset id to update.
        :param label: New display name (optional).
        :param current_value: New value in EUR (optional).
        :return: Dict with the updated asset data.
        :raises KeyError: If the asset is not found.
        """
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "SELECT id, label, current_value, updated_at FROM net_worth_assets WHERE id = ?",
                (id,)
            )
            row = cursor.fetchone()
            if not row:
                raise KeyError(f"Asset with id '{id}' not found")

            current_label = row[1]
            current_val = row[2]

            new_label = label if label is not None else current_label
            new_value = current_value if current_value is not None else current_val
            today = datetime.datetime.now().strftime('%Y-%m-%d')

            connection.execute(
                "UPDATE net_worth_assets SET label = ?, current_value = ?, updated_at = ? WHERE id = ?",
                (new_label, new_value, today, id)
            )
            connection.commit()

        return {
            "id": id,
            "label": new_label,
            "current_value": new_value,
            "updated_at": today,
        }

    @classmethod
    def deleteNetWorthAsset(cls, id: str) -> None:
        """
        Deletes a net worth asset category and its snapshots.

        :param id: The asset id to delete.
        :raises KeyError: If the asset is not found.
        """
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "SELECT id FROM net_worth_assets WHERE id = ?", (id,)
            )
            if not cursor.fetchone():
                raise KeyError(f"Asset with id '{id}' not found")

            connection.execute(
                "DELETE FROM net_worth_snapshots WHERE asset_id = ?", (id,)
            )
            connection.execute(
                "DELETE FROM net_worth_assets WHERE id = ?", (id,)
            )
            connection.commit()

    @classmethod
    def getNetWorthSnapshots(cls, start_date: str, end_date: str) -> list:
        """
        Fetches net worth snapshots within a date range.

        :param start_date: Start date (YYYY-MM-DD).
        :param end_date: End date (YYYY-MM-DD).
        :return: List of dicts with date, asset_id, value.
        """
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "SELECT date, asset_id, value FROM net_worth_snapshots "
                "WHERE date >= ? AND date <= ? ORDER BY date ASC",
                (start_date, end_date)
            )
            rows = cursor.fetchall()
        return [
            {"date": row[0], "asset_id": row[1], "value": row[2]}
            for row in rows
        ]

    @classmethod
    def addNetWorthSnapshot(cls, date: str, asset_id: str, value: float) -> None:
        """
        Adds or updates a net worth snapshot for a given date and asset.

        :param date: Snapshot date (YYYY-MM-DD).
        :param asset_id: The asset id.
        :param value: The value at snapshot date.
        """
        with get_connection(DB_PATH) as connection:
            connection.execute(
                "INSERT INTO net_worth_snapshots (date, asset_id, value) VALUES (?, ?, ?) "
                "ON CONFLICT(date, asset_id) DO UPDATE SET value = excluded.value",
                (date, asset_id, value)
            )
            connection.commit()

    @classmethod
    def getStockPriceHistory(cls, symbol: str, start_date: str = None, end_date: str = None) -> list:
        """
        Fetches historical price data for a single stock.

        :param symbol: The stock symbol.
        :param start_date: Optional start date filter (YYYY-MM-DD).
        :param end_date: Optional end date filter (YYYY-MM-DD).
        :return: List of dicts with datestamp and closeprice, ordered by date ascending.
        """
        symbol = symbol.upper()
        if symbol not in cls.symbol_map:
            return []

        stockid = cls.symbol_map[symbol]
        query = "SELECT datestamp, closeprice FROM historicalstocks WHERE stockid = ?"
        params = [stockid]

        if start_date:
            query += " AND datestamp >= ?"
            params.append(start_date)

        if end_date:
            query += " AND datestamp <= ?"
            params.append(end_date)

        query += " ORDER BY datestamp ASC"

        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(query, params)
            rows = cursor.fetchall()

        return [
            {"datestamp": row[0], "closeprice": row[1]}
            for row in rows
        ]

    @classmethod
    def updateHistoricalStocksPortfolio(cls, start_date: str, end_date: str) -> None:
        """
        Updates the historicalstocks table with data fetched from the StockAPI.

        :param start_date: Start date for the historical data (YYYY-MM-DD).
        :param end_date: End date for the historical data (YYYY-MM-DD).
        """
        symbols = [p.stock.symbol for p in cls.positions.values()]

        # Fetch the last timestamp from the table
        with get_connection(DB_PATH) as connection:
            answers = connection.execute('SELECT MAX(datestamp) FROM historicalstocks')
            last_timestamp = answers.fetchone()[0]

        historical_data = StockAPI.get_historical_data(symbols, last_timestamp)

        with get_connection(DB_PATH) as connection:
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
        historical_dividends = StockAPI.get_historical_dividends(symbols)

        with get_connection(DB_PATH) as connection:
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
        with get_connection(DB_PATH) as connection:
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
        with get_connection(DB_PATH) as connection:
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
        with get_connection(DB_PATH) as connection:
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
        Finds the next upcoming projected dividend across all portfolio positions.

        Uses the projection algorithm to determine the earliest future dividend
        based on historical payment patterns.

        Returns:
        - dict: Contains stockid, dividend_rate, and date (never returns None)
        """
        from datetime import datetime as dt, timedelta

        default_result = {'stockid': None, 'dividend_rate': 0.0, 'date': None}
        today = dt.now().strftime('%Y-%m-%d')
        end_date = (dt.now() + timedelta(days=365)).strftime('%Y-%m-%d')

        earliest = None
        try:
            for stockid in cls.positions:
                projected = cls._projectDividends(stockid, today, end_date)
                if projected:
                    first = projected[0]
                    if earliest is None or first["date"] < earliest["date"]:
                        earliest = {
                            'stockid': stockid,
                            'dividend_rate': first["amount_per_share"],
                            'date': first["date"],
                        }
        except Exception as e:
            logger.error(f"getNextDividendInfo(): Error projecting next dividend: {e}")

        return earliest if earliest else default_result

    @classmethod
    def getDividendCalendar(cls, start_date: str, end_date: str) -> list:
        """
        Returns dividend calendar events (historical + projected) for the given date range.

        :param start_date: Start date in YYYY-MM-DD format.
        :param end_date: End date in YYYY-MM-DD format.
        :return: List of dividend calendar event dicts sorted by date.
        """
        from datetime import datetime as dt, timedelta

        events = []
        # Track transaction dates per stock for proximity-based deduplication.
        # The ex-dividend date (yfinance) and payment date (transaction) for the
        # same dividend event can differ by up to ~30 days.
        tx_dates_by_stock = {}

        # Fetch dividend transactions (actual payments received) within the date range
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute('''
                SELECT DATE(t.datestamp) as d, t.price, t.stockid,
                       s.symbol, s.name, t.quantity
                FROM transactions t
                JOIN stocks s ON t.stockid = s.stockid
                WHERE t.type = 'DIVIDEND'
                  AND DATE(t.datestamp) >= ? AND DATE(t.datestamp) <= ?
                ORDER BY d ASC
            ''', (start_date, end_date))
            tx_rows = cursor.fetchall()

        for row in tx_rows:
            stockid = row[2]
            tx_dates_by_stock.setdefault(stockid, []).append(
                dt.strptime(row[0], '%Y-%m-%d')
            )
            events.append({
                "date": row[0],
                "symbol": row[3],
                "name": row[4],
                "amount_per_share": round(row[1], 4),
                "total_amount": round(row[1] * row[5], 2),
                "type": "historical",
            })

        # Fetch yfinance historical dividends only for stocks with NO dividend
        # transaction records at all. Transactions are the source of truth for
        # actual payments; yfinance historicaldividends includes all ex-dividend
        # dates regardless of whether the user held the stock.
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "SELECT DISTINCT stockid FROM transactions WHERE type = 'DIVIDEND'"
            )
            stocks_with_transactions = {row[0] for row in cursor.fetchall()}

        with get_connection(DB_PATH) as connection:
            cursor = connection.execute('''
                SELECT hd.datestamp, hd.dividendvalue, hd.stockid,
                       s.symbol, s.name
                FROM historicaldividends hd
                JOIN stocks s ON hd.stockid = s.stockid
                JOIN positions p ON hd.stockid = p.stockid
                WHERE hd.datestamp >= ? AND hd.datestamp <= ?
                ORDER BY hd.datestamp ASC
            ''', (start_date, end_date))
            hd_rows = cursor.fetchall()

        for row in hd_rows:
            stockid = row[2]
            # Skip stocks that have any transaction records — transactions are
            # the authoritative source for those stocks
            if stockid in stocks_with_transactions:
                continue
            quantity = cls.positions[stockid].quantity if stockid in cls.positions else 0
            events.append({
                "date": row[0],
                "symbol": row[3],
                "name": row[4],
                "amount_per_share": round(row[1], 4),
                "total_amount": round(row[1] * quantity, 2),
                "type": "historical",
            })

        # Generate projected dividends for each position
        for stockid, position in cls.positions.items():
            if position.stock is None:
                continue
            projected = cls._projectDividends(stockid, start_date, end_date)
            for proj in projected:
                events.append({
                    "date": proj["date"],
                    "symbol": position.stock.symbol,
                    "name": position.stock.name,
                    "amount_per_share": round(proj["amount_per_share"], 4),
                    "total_amount": round(proj["amount_per_share"] * position.quantity, 2),
                    "type": "projected",
                })

        events.sort(key=lambda e: e["date"])
        return events

    @classmethod
    def _projectDividends(cls, stockid: int, start_date: str, end_date: str) -> list:
        """
        Projects future dividend dates for a single stock based on historical payment patterns.

        Algorithm:
        1. Fetch all historical dividend dates for this stock, sorted ascending.
        2. If fewer than 2 records, return empty (cannot detect frequency).
        3. Calculate intervals (in days) between consecutive payments.
        4. Determine the median interval and classify frequency:
           - 80-100 days  -> quarterly (91 days)
           - 160-200 days -> semi-annual (182 days)
           - 330-400 days -> annual (365 days)
           - else         -> use the median interval directly
        5. Step forward from the last known dividend date by the frequency interval.
        6. Return projected dates within [start_date, end_date] that don't overlap historical dates.
        7. Use the most recent dividend amount as the projected amount.
        8. Cap projections at 12 months from the last known date.

        :return: List of dicts with "date" and "amount_per_share" keys.
        """
        from datetime import datetime as dt, timedelta
        from statistics import median

        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                'SELECT datestamp, dividendvalue FROM historicaldividends '
                'WHERE stockid = ? ORDER BY datestamp ASC',
                (stockid,)
            )
            rows = cursor.fetchall()

        if len(rows) < 2:
            return []

        dates = []
        amounts = []
        for row in rows:
            dates.append(dt.strptime(row[0], '%Y-%m-%d'))
            amounts.append(row[1])

        intervals = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]

        if not intervals:
            return []

        median_interval = median(intervals)

        if 80 <= median_interval <= 100:
            frequency_days = 91
        elif 160 <= median_interval <= 200:
            frequency_days = 182
        elif 330 <= median_interval <= 400:
            frequency_days = 365
        else:
            frequency_days = int(round(median_interval))

        last_date = dates[-1]
        last_amount = amounts[-1]
        historical_dates_set = {d.strftime('%Y-%m-%d') for d in dates}

        start_dt = dt.strptime(start_date, '%Y-%m-%d')
        end_dt = dt.strptime(end_date, '%Y-%m-%d')
        max_projection = last_date + timedelta(days=365)

        projected = []
        current = last_date + timedelta(days=frequency_days)

        while current <= min(end_dt, max_projection):
            date_str = current.strftime('%Y-%m-%d')
            if current >= start_dt and date_str not in historical_dates_set:
                projected.append({
                    "date": date_str,
                    "amount_per_share": last_amount,
                })
            current += timedelta(days=frequency_days)

        return projected