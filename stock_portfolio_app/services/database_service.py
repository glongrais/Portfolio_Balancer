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
    positions: Dict[int, Dict[int, Position]] = {}

    @classmethod
    def getPositionsForPortfolio(cls, portfolio_id: int) -> Dict[int, Position]:
        """Returns the positions dict for a given portfolio_id (stockid → Position)."""
        return cls.positions.get(portfolio_id, {})

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
            INSERT INTO stocks (symbol, name, price, currency, market_cap, sector, industry, country, logo_url, quote_type, ex_dividend_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                name=excluded.name,
                price=excluded.price,
                currency=excluded.currency,
                market_cap=excluded.market_cap,
                sector=excluded.sector,
                industry=excluded.industry,
                country=excluded.country,
                logo_url=excluded.logo_url,
                quote_type=excluded.quote_type,
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
                ticker_info.get("logo_url", ""),
                ticker_info.get("quoteType", "EQUITY"),
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
                logo_url = info.get("logo_url", "")
                if logo_url and not stock.logo_url:
                    stock.logo_url = logo_url
                    connection.execute(
                        'UPDATE stocks SET price = ?, logo_url = ? WHERE stockid = ?',
                        (info["currentPrice"], logo_url, stockid,)
                    )
                else:
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
        # Collect all unique positions across all portfolios
        all_positions = {}
        for portfolio_positions in cls.positions.values():
            for stockid, position in portfolio_positions.items():
                if stockid not in all_positions:
                    all_positions[stockid] = position

        if not all_positions:
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
                                (stockid, position) for stockid, position in all_positions.items()}

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
        Positions are stored as positions[portfolio_id][stockid] = Position.
        """
        cls.positions = {}
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
            pid = answer.portfolio_id
            if pid not in cls.positions:
                cls.positions[pid] = {}
            cls.positions[pid][answer.stockid] = answer
            log_count += 1
        logger.info("getPosition(): %d portfolio position(s) fetched from the database", log_count)
    
    @classmethod
    def addPosition(cls, symbol, quantity: float, distribution_target: float=None, portfolio_id: int=1) -> None:
        """
        Add a new position in the portfolio database and in-memory cache.

        :param symbol: The symbol of the stock in the position
        :param portfolio_id: The portfolio to add the position to
        """
        stockid = cls.addStock(symbol=symbol)

        portfolio_positions = cls.getPositionsForPortfolio(portfolio_id)
        if stockid in portfolio_positions:
            logger.warning("addPosition(): Position %s already in portfolio %d", symbol, portfolio_id)
            return
        with get_connection(DB_PATH) as connection:
            connection.execute("INSERT INTO positions (stockid, quantity, distribution_target, portfolio_id) VALUES (?, ?, ?, ?)", (stockid, quantity, distribution_target, portfolio_id))
            connection.commit()
        if portfolio_id not in cls.positions:
            cls.positions[portfolio_id] = {}
        cls.positions[portfolio_id][stockid] = Position(stockid=stockid, quantity=quantity,
                                          distribution_target=distribution_target,
                                          stock=cls.stocks[stockid], portfolio_id=portfolio_id)
        logger.info("addPosition(): Added position %s to portfolio %d", symbol, portfolio_id)

    @classmethod
    def updatePosition(cls, symbol, quantity: float=None, average_cost_basis: float=None, distribution_target: float=None, distribution_real: float=None, portfolio_id: int=1) -> None:
        """
        Update an existing position in the portfolio database and in-memory cache.

        :param symbol: The stock symbol of the position to update.
        :param quantity: The new quantity of the position (default is None).
        :param distribution_target: The new target distribution of the position (default is None).
        :param distribution_real: The new real distribution of the position (default is None).
        :param portfolio_id: The portfolio the position belongs to.
        """
        if symbol not in cls.symbol_map:
            logger.warning("updatePosition(): Position %s not in the portfolio", symbol)
            return

        stockid = cls.symbol_map[symbol]
        portfolio_positions = cls.getPositionsForPortfolio(portfolio_id)
        if stockid not in portfolio_positions:
            logger.warning("updatePosition(): Position %s not in portfolio %d", symbol, portfolio_id)
            return

        position = portfolio_positions[stockid]
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

        params.extend([stockid, portfolio_id])
        query = "UPDATE positions SET " + ", ".join(fields_to_update) + " WHERE stockid = ? AND portfolio_id = ?"

        with get_connection(DB_PATH) as connection:
            connection.execute(query, params)
            connection.commit()

        logger.debug(
            "updatePosition(): Position %s updated in portfolio %d. Quantity: %s, Average cost basis: %s, Distribution target: %s, Distribution real: %s",
            symbol, portfolio_id, position.quantity, position.average_cost_basis, position.distribution_target, position.distribution_real
        )

    @classmethod
    def removePosition(cls, symbol: str, portfolio_id: int = 1) -> None:
        """
        Remove a position from the portfolio. Requires quantity to be 0.
        Stock record and transaction history are preserved.

        :param symbol: The stock symbol of the position to remove.
        :param portfolio_id: The portfolio the position belongs to.
        :raises KeyError: If the stock or position is not found.
        :raises ValueError: If the position still has shares.
        """
        if symbol not in cls.symbol_map:
            raise KeyError(f"Stock with symbol '{symbol}' not found")

        stockid = cls.symbol_map[symbol]
        portfolio_positions = cls.getPositionsForPortfolio(portfolio_id)
        if stockid not in portfolio_positions:
            raise KeyError(f"Position for '{symbol}' not found in portfolio {portfolio_id}")

        current_qty = portfolio_positions[stockid].quantity
        if current_qty != 0:
            raise ValueError(
                f"Cannot remove position '{symbol}': quantity is {current_qty}. Sell all shares first."
            )

        with get_connection(DB_PATH) as connection:
            connection.execute("DELETE FROM positions WHERE stockid = ? AND portfolio_id = ?", (stockid, portfolio_id))
            connection.commit()

        del cls.positions[portfolio_id][stockid]
        logger.info("removePosition(): Removed position %s from portfolio %d", symbol, portfolio_id)

    @classmethod
    def upsertTransactions(cls, date: datetime, rowid: int, type: str, symbol: str, quantity: float, price: float, portfolio_id: int = 1) -> None:
        """
        Add or update a transaction in the database.
        For buy/sell transactions, automatically updates position quantity if the position exists.

        :param date: The date of the transaction.
        :param type: The type of the transaction (buy or sell).
        :param symbol: The symbol of the stock in the transaction.
        :param quantity: The quantity of the stock in the transaction.
        :param price: The price of the stock in the transaction.
        :param portfolio_id: The portfolio this transaction belongs to.
        :raises ValueError: If selling more shares than currently held.
        """
        stockid = cls.getStock(symbol=symbol)
        if stockid == -1:
            stockid = cls.addStock(symbol)

        portfolio_positions = cls.getPositionsForPortfolio(portfolio_id)

        # Validate sell quantity before inserting the transaction
        if type == 'sell' and stockid in portfolio_positions:
            current_qty = portfolio_positions[stockid].quantity
            if quantity > current_qty:
                raise ValueError(
                    f"Cannot sell {quantity} shares of {symbol}: only {current_qty} shares held"
                )

        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "INSERT INTO transactions (stockid, portfolioid, rowid, quantity, price, type, datestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(portfolioid, rowid) DO NOTHING",
                (stockid, portfolio_id, rowid, quantity, price, type, date,)
            )
            connection.commit()
            rows_inserted = cursor.rowcount

        logger.info("upsertTransactions(): Transaction added for stock %s in portfolio %d", symbol, portfolio_id)

        # Auto-update position quantity if a row was actually inserted
        if rows_inserted > 0 and stockid in portfolio_positions:
            old_qty = portfolio_positions[stockid].quantity
            if type == 'sell':
                new_qty = old_qty - quantity
                cls.updatePosition(symbol, quantity=new_qty, portfolio_id=portfolio_id)
                logger.info(
                    "upsertTransactions(): Sold %d shares of %s. Position quantity: %d -> %d",
                    quantity, symbol, old_qty, new_qty
                )
            elif type == 'buy':
                new_qty = old_qty + quantity
                cls.updatePosition(symbol, quantity=new_qty, portfolio_id=portfolio_id)
                logger.info(
                    "upsertTransactions(): Bought %d shares of %s. Position quantity: %d -> %d",
                    quantity, symbol, old_qty, new_qty
                )

    @classmethod
    def getTransactions(cls, symbol: str = None, transaction_type: str = None, limit: int = 100, portfolio_id: int = 1) -> list:
        """
        Fetches transaction history from the database with optional filtering.

        :param symbol: Filter by stock symbol (optional).
        :param transaction_type: Filter by transaction type - buy/sell (optional).
        :param limit: Maximum number of transactions to return.
        :param portfolio_id: The portfolio to fetch transactions for.
        :return: List of transaction dicts.
        """
        query = ("SELECT t.transactionid, t.stockid, s.symbol, t.quantity, t.price, t.type, t.datestamp, s.name "
                 "FROM transactions t JOIN stocks s ON t.stockid = s.stockid")
        params = []
        conditions = ["t.portfolioid = ?"]
        params.append(portfolio_id)

        if symbol:
            conditions.append("s.symbol = ?")
            params.append(symbol.upper())

        if transaction_type:
            conditions.append("t.type = ?")
            params.append(transaction_type.lower())

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
    def getTransactionSummary(cls, symbol: str = None, portfolio_id: int = 1) -> list:
        """
        Gets transaction summary statistics, optionally filtered by symbol.

        :param symbol: Filter by stock symbol (optional).
        :param portfolio_id: The portfolio to fetch summary for.
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
            WHERE t.portfolioid = ?
        """
        params = [portfolio_id]

        if symbol:
            query += " AND s.symbol = ?"
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
    def getDeposits(cls, limit: int = 100, portfolio_id: int = 1) -> list:
        """
        Fetches deposit history from the database.

        :param limit: Maximum number of deposits to return.
        :param portfolio_id: The portfolio to fetch deposits for.
        :return: List of deposit dicts.
        """
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "SELECT depositid, datestamp, amount, portfolioid, currency FROM deposits WHERE portfolioid = ? ORDER BY datestamp DESC LIMIT ?",
                (portfolio_id, limit,)
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
    def getTotalDeposits(cls, portfolio_id: int = 1) -> float:
        """
        Calculates the total amount deposited.

        :param portfolio_id: The portfolio to calculate total for.
        :return: Total deposit amount.
        """
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute("SELECT COALESCE(SUM(amount), 0) FROM deposits WHERE portfolioid = ?", (portfolio_id,))
            total = cursor.fetchone()[0]
        return round(total, 2)

    @classmethod
    def addDeposit(cls, datestamp: str, amount: float, portfolio_id: int = 1) -> dict:
        """
        Adds a new deposit to the database.

        :param datestamp: The deposit date (YYYY-MM-DD string).
        :param amount: The deposit amount.
        :param portfolio_id: The portfolio to add the deposit to.
        :return: Dict with the created deposit data.
        """
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "INSERT INTO deposits (datestamp, amount, portfolioid, currency) VALUES (?, ?, ?, 'EUR')",
                (datestamp, amount, portfolio_id)
            )
            connection.commit()
            deposit_id = cursor.lastrowid
        return {
            "depositid": deposit_id,
            "datestamp": datestamp,
            "amount": amount,
            "portfolioid": portfolio_id,
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
    def getEquityGrants(cls) -> list:
        """
        Fetches all equity grants with their vesting events and computed values.

        :return: List of grant dicts with vested/unvested computation.
        """
        today = datetime.datetime.now().strftime('%Y-%m-%d')

        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "SELECT id, name, stockid, total_shares, grant_date, grant_price FROM equity_grants ORDER BY id ASC"
            )
            grants = cursor.fetchall()

        result = []
        for grant in grants:
            grant_id, name, stockid, total_shares, grant_date, grant_price = grant
            result.append(cls._buildEquityGrantDict(
                grant_id, name, stockid, total_shares, grant_date, grant_price, today
            ))
        return result

    @classmethod
    def getEquityGrant(cls, grant_id: int) -> dict:
        """
        Fetches a single equity grant with computed values.

        :param grant_id: The grant ID.
        :return: Grant dict with vested/unvested computation.
        :raises KeyError: If the grant is not found.
        """
        today = datetime.datetime.now().strftime('%Y-%m-%d')

        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "SELECT id, name, stockid, total_shares, grant_date, grant_price FROM equity_grants WHERE id = ?",
                (grant_id,)
            )
            row = cursor.fetchone()

        if not row:
            raise KeyError(f"Grant with id {grant_id} not found")

        grant_id, name, stockid, total_shares, grant_date, grant_price = row
        return cls._buildEquityGrantDict(
            grant_id, name, stockid, total_shares, grant_date, grant_price, today
        )

    @classmethod
    def _buildEquityGrantDict(cls, grant_id: int, name: str, stockid: int, total_shares: int, grant_date: str, grant_price: float, today: str) -> dict:
        """
        Builds a grant response dict with live price, FX rate, vested/unvested computation, and gain/loss.
        """
        # Get stock info
        stock = cls.stocks.get(stockid)
        if stock is None:
            cls.getStock(stockid=stockid)
            stock = cls.stocks.get(stockid)

        symbol = stock.symbol if stock else "UNKNOWN"
        stock_name = stock.name if stock else ""
        currency = stock.currency if stock else "USD"

        # Fetch live price and FX rate
        try:
            price_info = StockAPI.get_current_price(symbol)
            share_price = price_info.get("currentPrice", 0.0) or 0.0
        except Exception:
            share_price = stock.price if stock else 0.0

        fx_rate = StockAPI.get_fx_rate(currency, "EUR")

        # Fetch vesting events
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "SELECT id, grant_id, date, shares, taxed_shares FROM equity_vesting_events "
                "WHERE grant_id = ? ORDER BY date ASC",
                (grant_id,)
            )
            events = cursor.fetchall()

        vesting_events = []
        vested_shares = 0
        for event in events:
            taxed = event[4] if event[4] else 0
            net = event[3] - taxed
            is_vested = event[2] <= today
            vesting_events.append({
                "id": event[0],
                "grant_id": event[1],
                "date": event[2],
                "shares": event[3],
                "taxed_shares": taxed,
                "net_shares": net,
                "vested": is_vested,
            })
            if is_vested:
                vested_shares += net

        unvested_shares = total_shares - vested_shares
        vested_value = round(vested_shares * share_price, 2)
        unvested_value = round(unvested_shares * share_price, 2)
        total_value = round(total_shares * share_price, 2)
        gain_loss = round((share_price - grant_price) * vested_shares, 2)
        gain_loss_pct = round((share_price - grant_price) / grant_price * 100, 2) if grant_price > 0 else 0.0

        return {
            "id": grant_id,
            "name": name,
            "symbol": symbol,
            "stock_name": stock_name,
            "total_shares": total_shares,
            "grant_date": grant_date,
            "grant_price": round(grant_price, 2),
            "share_price": round(share_price, 2),
            "currency": currency,
            "fx_rate": round(fx_rate, 6),
            "vested_shares": vested_shares,
            "unvested_shares": unvested_shares,
            "vested_value": vested_value,
            "unvested_value": unvested_value,
            "total_value": total_value,
            "gain_loss": gain_loss,
            "gain_loss_pct": gain_loss_pct,
            "vesting_events": vesting_events,
        }

    @classmethod
    def addEquityGrant(cls, name: str, symbol: str, total_shares: int, grant_date: str, grant_price: float, vesting_events: list) -> dict:
        """
        Creates a new equity grant with optional vesting events.

        :param name: Grant name.
        :param symbol: Stock ticker symbol.
        :param total_shares: Total shares granted.
        :param grant_date: Grant date (YYYY-MM-DD).
        :param grant_price: Share price at grant date.
        :param vesting_events: List of dicts with 'date' and 'shares'.
        :return: Created grant dict.
        :raises ValueError: If vesting events exceed total_shares.
        """
        event_total = sum(e["shares"] for e in vesting_events)
        if event_total > total_shares:
            raise ValueError(
                f"Vesting events total ({event_total}) exceeds total_shares ({total_shares})"
            )

        stockid = cls.addStock(symbol)

        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "INSERT INTO equity_grants (name, stockid, total_shares, grant_date, grant_price) VALUES (?, ?, ?, ?, ?)",
                (name, stockid, total_shares, grant_date, grant_price)
            )
            grant_id = cursor.lastrowid

            for event in vesting_events:
                connection.execute(
                    "INSERT INTO equity_vesting_events (grant_id, date, shares, taxed_shares) VALUES (?, ?, ?, ?)",
                    (grant_id, event["date"], event["shares"], event.get("taxed_shares", 0))
                )
            connection.commit()

        return cls.getEquityGrant(grant_id)

    @classmethod
    def updateEquityGrant(cls, grant_id: int, name: str = None) -> dict:
        """
        Updates equity grant metadata.

        :param grant_id: The grant ID.
        :param name: New grant name (optional).
        :return: Updated grant dict.
        :raises KeyError: If the grant is not found.
        """
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "SELECT id FROM equity_grants WHERE id = ?", (grant_id,)
            )
            if not cursor.fetchone():
                raise KeyError(f"Grant with id {grant_id} not found")

            if name is not None:
                connection.execute(
                    "UPDATE equity_grants SET name = ? WHERE id = ?",
                    (name, grant_id)
                )
                connection.commit()

        return cls.getEquityGrant(grant_id)

    @classmethod
    def deleteEquityGrant(cls, grant_id: int) -> None:
        """
        Deletes an equity grant and its vesting events.

        :param grant_id: The grant ID.
        :raises KeyError: If the grant is not found.
        """
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "SELECT id FROM equity_grants WHERE id = ?", (grant_id,)
            )
            if not cursor.fetchone():
                raise KeyError(f"Grant with id {grant_id} not found")

            connection.execute(
                "DELETE FROM equity_vesting_events WHERE grant_id = ?", (grant_id,)
            )
            connection.execute(
                "DELETE FROM equity_grants WHERE id = ?", (grant_id,)
            )
            connection.commit()

    @classmethod
    def addEquityVestingEvent(cls, grant_id: int, date: str, shares: int, taxed_shares: int = 0) -> dict:
        """
        Adds a vesting event to a grant.

        :param grant_id: The grant ID.
        :param date: Vesting date (YYYY-MM-DD).
        :param shares: Number of shares vesting (gross).
        :param taxed_shares: Shares withheld for tax.
        :return: Created event dict.
        :raises KeyError: If the grant is not found.
        :raises ValueError: If adding this event would exceed total_shares.
        """
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "SELECT total_shares FROM equity_grants WHERE id = ?", (grant_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise KeyError(f"Grant with id {grant_id} not found")

            total_shares = row[0]

            cursor = connection.execute(
                "SELECT COALESCE(SUM(shares), 0) FROM equity_vesting_events WHERE grant_id = ?",
                (grant_id,)
            )
            current_total = cursor.fetchone()[0]

            if current_total + shares > total_shares:
                raise ValueError(
                    f"Adding {shares} shares would exceed total_shares ({total_shares}). "
                    f"Current vesting total: {current_total}"
                )

            cursor = connection.execute(
                "INSERT INTO equity_vesting_events (grant_id, date, shares, taxed_shares) VALUES (?, ?, ?, ?)",
                (grant_id, date, shares, taxed_shares)
            )
            event_id = cursor.lastrowid
            connection.commit()

        today = datetime.datetime.now().strftime('%Y-%m-%d')
        return {
            "id": event_id,
            "grant_id": grant_id,
            "date": date,
            "shares": shares,
            "taxed_shares": taxed_shares,
            "net_shares": shares - taxed_shares,
            "vested": date <= today,
        }

    @classmethod
    def updateEquityVestingEvent(cls, event_id: int, date: str = None, shares: int = None, taxed_shares: int = None) -> dict:
        """
        Updates a vesting event.

        :param event_id: The vesting event ID.
        :param date: New vesting date (optional).
        :param shares: New number of shares (optional).
        :param taxed_shares: New taxed shares (optional).
        :return: Updated event dict.
        :raises KeyError: If the event is not found.
        :raises ValueError: If new shares would exceed total_shares.
        """
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "SELECT id, grant_id, date, shares, taxed_shares FROM equity_vesting_events WHERE id = ?",
                (event_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise KeyError(f"Vesting event with id {event_id} not found")

            current_grant_id = row[1]
            new_date = date if date is not None else row[2]
            new_shares = shares if shares is not None else row[3]
            new_taxed = taxed_shares if taxed_shares is not None else (row[4] or 0)

            # Validate total doesn't exceed total_shares if shares changed
            if shares is not None:
                cursor = connection.execute(
                    "SELECT total_shares FROM equity_grants WHERE id = ?", (current_grant_id,)
                )
                total_shares = cursor.fetchone()[0]

                cursor = connection.execute(
                    "SELECT COALESCE(SUM(shares), 0) FROM equity_vesting_events "
                    "WHERE grant_id = ? AND id != ?",
                    (current_grant_id, event_id)
                )
                other_total = cursor.fetchone()[0]

                if other_total + new_shares > total_shares:
                    raise ValueError(
                        f"Updating to {new_shares} shares would exceed total_shares ({total_shares}). "
                        f"Other events total: {other_total}"
                    )

            connection.execute(
                "UPDATE equity_vesting_events SET date = ?, shares = ?, taxed_shares = ? WHERE id = ?",
                (new_date, new_shares, new_taxed, event_id)
            )
            connection.commit()

        today = datetime.datetime.now().strftime('%Y-%m-%d')
        return {
            "id": event_id,
            "grant_id": current_grant_id,
            "date": new_date,
            "shares": new_shares,
            "taxed_shares": new_taxed,
            "net_shares": new_shares - new_taxed,
            "vested": new_date <= today,
        }

    @classmethod
    def deleteEquityVestingEvent(cls, event_id: int) -> None:
        """
        Deletes a vesting event.

        :param event_id: The vesting event ID.
        :raises KeyError: If the event is not found.
        """
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "SELECT id FROM equity_vesting_events WHERE id = ?", (event_id,)
            )
            if not cursor.fetchone():
                raise KeyError(f"Vesting event with id {event_id} not found")

            connection.execute(
                "DELETE FROM equity_vesting_events WHERE id = ?", (event_id,)
            )
            connection.commit()

    @classmethod
    def getEquityVestedTotal(cls) -> float:
        """
        Computes the total vested equity value in EUR across all grants.

        :return: Total vested value in EUR.
        """
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        total = 0.0

        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "SELECT id, stockid, total_shares FROM equity_grants"
            )
            grants = cursor.fetchall()

        for grant in grants:
            grant_id, stockid, total_shares = grant

            stock = cls.stocks.get(stockid)
            if stock is None:
                continue

            try:
                price_info = StockAPI.get_current_price(stock.symbol)
                share_price = price_info.get("currentPrice", 0.0) or 0.0
            except Exception:
                share_price = stock.price or 0.0

            fx_rate = StockAPI.get_fx_rate(stock.currency or "EUR", "EUR")

            with get_connection(DB_PATH) as connection:
                cursor = connection.execute(
                    "SELECT COALESCE(SUM(shares - taxed_shares), 0) FROM equity_vesting_events "
                    "WHERE grant_id = ? AND date <= ?",
                    (grant_id, today)
                )
                vested_shares = cursor.fetchone()[0]

            total += vested_shares * share_price * fx_rate

        return round(total, 2)

    @classmethod
    def getEquitySummary(cls) -> dict:
        """
        Computes an aggregated equity summary across all grants.

        :return: Dict with total vested/unvested values, gain/loss, and grant count.
        """
        grants = cls.getEquityGrants()

        total_vested = 0.0
        total_unvested = 0.0
        total_gain_loss = 0.0
        total_grant_cost = 0.0

        for g in grants:
            total_vested += g["vested_value"]
            total_unvested += g["unvested_value"]
            total_gain_loss += g["gain_loss"]
            total_grant_cost += g["vested_shares"] * g["grant_price"]

        total_gain_loss_pct = round(total_gain_loss / total_grant_cost * 100, 2) if total_grant_cost > 0 else 0.0
        currency = grants[0]["currency"] if grants else "USD"

        return {
            "total_vested_value": round(total_vested, 2),
            "total_unvested_value": round(total_unvested, 2),
            "total_gain_loss": round(total_gain_loss, 2),
            "total_gain_loss_pct": total_gain_loss_pct,
            "grants_count": len(grants),
            "currency": currency,
        }

    @classmethod
    def getEquityValueHistory(cls, start_date: str, end_date: str, target_dates: list = None, convert_to_eur: bool = False) -> list:
        """
        Computes historical equity vested value for a set of target dates.

        For each target date, uses the latest available stock price and FX rate
        up to that date, so equity appears from the vesting date onward even if
        historical price data is sparse.

        :param start_date: Start date (YYYY-MM-DD).
        :param end_date: End date (YYYY-MM-DD).
        :param target_dates: Sorted list of date strings to compute values for.
                             If None, uses dates from historicalstocks.
        :return: List of (date_str, value_eur) tuples.
        """
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute(
                "SELECT eg.id, eg.stockid, COALESCE(s.currency, 'EUR') "
                "FROM equity_grants eg JOIN stocks s ON eg.stockid = s.stockid"
            )
            grants = cursor.fetchall()

        if not grants:
            return []

        result = {}  # date -> total equity value

        for grant_id, stockid, currency in grants:
            # Get vesting events sorted by date
            with get_connection(DB_PATH) as connection:
                cursor = connection.execute(
                    "SELECT date, (shares - taxed_shares) as net "
                    "FROM equity_vesting_events WHERE grant_id = ? ORDER BY date ASC",
                    (grant_id,)
                )
                events = cursor.fetchall()

            if not events:
                continue

            # Get ALL historical prices up to end_date (including before start_date
            # so we can carry forward the latest price)
            with get_connection(DB_PATH) as connection:
                cursor = connection.execute(
                    "SELECT datestamp, closeprice FROM historicalstocks "
                    "WHERE stockid = ? AND datestamp <= ? "
                    "ORDER BY datestamp ASC",
                    (stockid, end_date)
                )
                all_prices = cursor.fetchall()

            # Build price lookup dict for forward-fill
            price_by_date = {row[0]: row[1] for row in all_prices}
            price_dates_sorted = [row[0] for row in all_prices]

            if not all_prices:
                continue

            # Build FX rate lookup (only needed when converting to EUR)
            fx_lookup = {}
            if convert_to_eur and currency and currency != "EUR":
                pair = f"{currency}EUR"
                with get_connection(DB_PATH) as connection:
                    cursor = connection.execute(
                        "SELECT date, rate FROM fx_rates_history "
                        "WHERE pair = ? AND date <= ? "
                        "ORDER BY date ASC",
                        (pair, end_date)
                    )
                    fx_lookup = {row[0]: row[1] for row in cursor.fetchall()}

            # Determine which dates to iterate over
            if target_dates is not None:
                dates_to_process = target_dates
            else:
                dates_to_process = [d for d in price_dates_sorted if d >= start_date]

            # Walk through target dates
            cumulative_vested = 0
            event_idx = 0
            last_price = None
            last_fx = 1.0
            price_idx = 0

            # Pre-accumulate vesting events before first target date
            first_date = dates_to_process[0] if dates_to_process else start_date
            while event_idx < len(events) and events[event_idx][0] < first_date:
                cumulative_vested += events[event_idx][1]
                event_idx += 1

            # Pre-fill last_price from prices before first target date
            for p_date, p_val in all_prices:
                if p_date < first_date:
                    last_price = p_val
                else:
                    break

            # Pre-fill last_fx from rates before first target date
            if convert_to_eur and currency and currency != "EUR":
                for fx_date in sorted(fx_lookup.keys()):
                    if fx_date < first_date:
                        last_fx = fx_lookup[fx_date]
                    else:
                        break

            for date_str in dates_to_process:
                # Accumulate vesting events up to this date
                while event_idx < len(events) and events[event_idx][0] <= date_str:
                    cumulative_vested += events[event_idx][1]
                    event_idx += 1

                if cumulative_vested <= 0:
                    continue

                # Forward-fill price: use exact match or carry forward last known
                if date_str in price_by_date:
                    last_price = price_by_date[date_str]

                if last_price is None:
                    continue

                # Forward-fill FX rate (only when converting to EUR)
                if convert_to_eur and currency and currency != "EUR":
                    if date_str in fx_lookup:
                        last_fx = fx_lookup[date_str]

                value = cumulative_vested * last_price * (last_fx if convert_to_eur else 1.0)
                result[date_str] = result.get(date_str, 0.0) + value

        return sorted(result.items())

    @classmethod
    def updateFxRatesHistory(cls, pairs: list) -> None:
        """
        Fetches and stores historical FX rates for given currency pairs.

        :param pairs: List of currency pair strings (e.g. ['USDEUR', 'SEKEUR']).
        """
        for pair in pairs:
            # Get the last stored date for this pair
            with get_connection(DB_PATH) as connection:
                cursor = connection.execute(
                    "SELECT MAX(date) FROM fx_rates_history WHERE pair = ?", (pair,)
                )
                last_date = cursor.fetchone()[0]

            start_date = last_date if last_date else "2020-01-01"
            rates = StockAPI.get_historical_fx_rates(pair, start_date)

            if not rates:
                continue

            with get_connection(DB_PATH) as connection:
                for date_str, rate in rates:
                    connection.execute(
                        "INSERT INTO fx_rates_history (pair, date, rate) VALUES (?, ?, ?) "
                        "ON CONFLICT(pair, date) DO UPDATE SET rate = excluded.rate",
                        (pair, date_str, rate)
                    )
                connection.commit()
            logger.info("updateFxRatesHistory(): Updated %d rate(s) for %s", len(rates), pair)

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
    def _insertHistoricalData(cls, historical_data) -> None:
        """Inserts historical stock data rows into the database."""
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

    @classmethod
    def updateHistoricalStocksPortfolio(cls, start_date: str, end_date: str) -> None:
        """
        Updates the historicalstocks table with data fetched from the StockAPI.
        Includes both portfolio position stocks and equity grant stocks.

        For each stock, fetches from its own MAX(datestamp) if it has data,
        or from the beginning ('max' period) if it has no data yet.
        """
        # Collect all symbols: portfolio positions + equity grants
        all_symbols = set()
        for portfolio_positions in cls.positions.values():
            for p in portfolio_positions.values():
                all_symbols.add(p.stock.symbol)
        with get_connection(DB_PATH) as connection:
            cursor = connection.execute("SELECT DISTINCT stockid FROM equity_grants")
            for row in cursor.fetchall():
                stock = cls.stocks.get(row[0])
                if stock:
                    all_symbols.add(stock.symbol)

        # For each stock, find its last known date
        # Group symbols by start date to minimize API calls
        from collections import defaultdict
        by_start = defaultdict(list)  # start_date -> [symbols]
        for symbol in all_symbols:
            stockid = cls.symbol_map.get(symbol)
            if stockid is None:
                continue
            with get_connection(DB_PATH) as connection:
                row = connection.execute(
                    "SELECT MAX(datestamp) FROM historicalstocks WHERE stockid = ?",
                    (stockid,)
                ).fetchone()
                last_date = row[0]
            by_start[last_date].append(symbol)

        # Fetch and insert for each group
        total = 0
        for last_date, symbols in by_start.items():
            if last_date is None:
                # No data yet — fetch full history
                logger.info("Full history fetch for: %s", ", ".join(symbols))
                data = StockAPI.get_historical_data(symbols, start_date, end_date)
            else:
                data = StockAPI.get_historical_data(symbols, last_date, end_date)
            cls._insertHistoricalData(data)
            total += len(symbols)

        logger.info("updateHistoricalStocks(): Historical data updated for %d symbol(s)", total)
    
    @classmethod
    def updateHistoricalDividendsPortfolio(cls) -> None:
        """
        Updates the historicaldividends table with data fetched from the StockAPI.

        :param symbols: List of stock symbols to fetch historical dividends for.
        """

        symbols = [p.stock.symbol for portfolio_positions in cls.positions.values() for p in portfolio_positions.values()]
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
    def getPortfolioValueHistory(cls, portfolio_id: int = 1) -> list:
        """
        Retrieves the portfolio value history for a specific portfolio.

        :param portfolio_id: The portfolio to fetch history for.
        Returns:
        - list: Portfolio value history
        """
        with get_connection(DB_PATH) as connection:
            answers = connection.execute('''
                WITH
                transactions_buy AS (
                    SELECT stockid, strftime('%Y-%m-%d', datestamp) AS datestamp, quantity
                    FROM transactions
                    WHERE type = 'BUY' AND portfolioid = ?
                ),
                transactions_sell AS (
                    SELECT stockid, strftime('%Y-%m-%d', datestamp) AS datestamp, -quantity as quantity
                    FROM transactions
                    WHERE type = 'SELL' AND portfolioid = ?
                ),
                transactions_union AS (
                    SELECT * FROM transactions_buy
                    UNION ALL
                    SELECT * FROM transactions_sell
                ),
                daily_transactions AS (
                    SELECT stockid, datestamp, SUM(quantity) AS daily_quantity
                    FROM transactions_union
                    GROUP BY stockid, datestamp
                ),
                cumulative_positions AS (
                    SELECT stockid, datestamp,
                           SUM(daily_quantity) OVER (PARTITION BY stockid ORDER BY datestamp) AS cumulative_quantity
                    FROM daily_transactions
                ),
                filled_cumulative_datestamp AS (
                    SELECT
                        hs.datestamp, hs.stockid, hs.closeprice,
                        cp.cumulative_quantity,
                        MAX(hs.datestamp) FILTER (WHERE cp.cumulative_quantity > 0)
                            OVER (PARTITION BY hs.stockid ORDER BY hs.datestamp ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                            AS last_updated_datestamp
                    FROM historicalstocks hs
                    LEFT JOIN cumulative_positions cp
                        ON hs.datestamp = cp.datestamp AND hs.stockid = cp.stockid
                    WHERE hs.datestamp >= (SELECT MIN(datestamp) FROM cumulative_positions)
                ),
                filled_cumulative_quantity AS (
                    SELECT fcd.closeprice, fcd.datestamp, fcd.stockid,
                           cp2.cumulative_quantity AS filled_cumulative_quantity
                    FROM filled_cumulative_datestamp fcd
                    LEFT JOIN cumulative_positions cp2
                        ON fcd.last_updated_datestamp = cp2.datestamp AND fcd.stockid = cp2.stockid
                )
                SELECT datestamp, ROUND(SUM(filled_cumulative_quantity * closeprice), 2) AS portfolio_value
                FROM filled_cumulative_quantity
                GROUP BY datestamp
                ORDER BY datestamp
            ''', (portfolio_id, portfolio_id))
            rows = answers.fetchall()
        return rows
    
    @classmethod
    def getDividendTotal(cls, portfolio_id: int = 1) -> float:
        """
        Calculates the total yearly dividend for the portfolio.

        :param portfolio_id: The portfolio to calculate dividends for.
        Returns:
        - float: Total yearly dividend
        """
        total_dividend = 0.0
        with get_connection(DB_PATH) as connection:
            answers = connection.execute(
                "SELECT COALESCE(SUM(quantity * price), 0) FROM transactions WHERE type = 'DIVIDEND' AND portfolioid = ?",
                (portfolio_id,)
            )
            total_dividend = float(answers.fetchone()[0])
        return round(total_dividend, 2)

    @classmethod
    def getDividendYearToDate(cls, year: str, portfolio_id: int = 1) -> float:
        """
        Calculates the total dividends received for a given year.

        Args:
        - year: The year to calculate dividends for (e.g., '2024')
        - portfolio_id: The portfolio to calculate dividends for.

        Returns:
        - float: Total dividends for the year
        """
        with get_connection(DB_PATH) as connection:
            result = connection.execute(
                '''SELECT COALESCE(SUM(quantity * price), 0)
                   FROM transactions
                   WHERE type = 'DIVIDEND' AND portfolioid = ? AND strftime('%Y', datestamp) = ?''',
                (portfolio_id, year,)
            )
            row = result.fetchone()
            return round(row[0], 2) if row[0] else 0.0

    @classmethod
    def getNextDividendInfo(cls, portfolio_id: int = 1) -> dict:
        """
        Finds the next upcoming projected dividend across all portfolio positions.

        Uses the projection algorithm to determine the earliest future dividend
        based on historical payment patterns.

        :param portfolio_id: The portfolio to check dividends for.
        Returns:
        - dict: Contains stockid, dividend_rate, and date (never returns None)
        """
        from datetime import datetime as dt, timedelta

        default_result = {'stockid': None, 'dividend_rate': 0.0, 'date': None}
        today = dt.now().strftime('%Y-%m-%d')
        end_date = (dt.now() + timedelta(days=365)).strftime('%Y-%m-%d')

        portfolio_positions = cls.getPositionsForPortfolio(portfolio_id)
        earliest = None
        try:
            for stockid in portfolio_positions:
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
    def getDividendCalendar(cls, start_date: str, end_date: str, portfolio_id: int = 1) -> list:
        """
        Returns dividend calendar events (historical + projected) for the given date range.

        :param start_date: Start date in YYYY-MM-DD format.
        :param end_date: End date in YYYY-MM-DD format.
        :param portfolio_id: The portfolio to fetch dividend calendar for.
        :return: List of dividend calendar event dicts sorted by date.
        """
        from datetime import datetime as dt, timedelta

        events = []
        portfolio_positions = cls.getPositionsForPortfolio(portfolio_id)
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
                  AND t.portfolioid = ?
                  AND DATE(t.datestamp) >= ? AND DATE(t.datestamp) <= ?
                ORDER BY d ASC
            ''', (portfolio_id, start_date, end_date))
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
                "SELECT DISTINCT stockid FROM transactions WHERE type = 'DIVIDEND' AND portfolioid = ?",
                (portfolio_id,)
            )
            stocks_with_transactions = {row[0] for row in cursor.fetchall()}

        with get_connection(DB_PATH) as connection:
            cursor = connection.execute('''
                SELECT hd.datestamp, hd.dividendvalue, hd.stockid,
                       s.symbol, s.name
                FROM historicaldividends hd
                JOIN stocks s ON hd.stockid = s.stockid
                JOIN positions p ON hd.stockid = p.stockid
                WHERE p.portfolio_id = ?
                  AND hd.datestamp >= ? AND hd.datestamp <= ?
                ORDER BY hd.datestamp ASC
            ''', (portfolio_id, start_date, end_date))
            hd_rows = cursor.fetchall()

        for row in hd_rows:
            stockid = row[2]
            # Skip stocks that have any transaction records — transactions are
            # the authoritative source for those stocks
            if stockid in stocks_with_transactions:
                continue
            quantity = portfolio_positions[stockid].quantity if stockid in portfolio_positions else 0
            events.append({
                "date": row[0],
                "symbol": row[3],
                "name": row[4],
                "amount_per_share": round(row[1], 4),
                "total_amount": round(row[1] * quantity, 2),
                "type": "historical",
            })

        # Generate projected dividends for each position
        for stockid, position in portfolio_positions.items():
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