
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict
from services.database_service import DatabaseService
from models.Stock import Stock
from models.Position import Position

MOCK_PRICE = {
    "currentPrice": 100.0,
    "longName": "Apple Inc.",
    "symbol": "AAPL",
    "currency": "USD",
    "marketCap": 1000000000000,
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "country": "US"
}

@pytest.fixture
def setup_database_service():
    # Reset the class variables before each test
    DatabaseService.symbol_map = {}
    DatabaseService.stocks = {}
    DatabaseService.positions = {}
    yield

@patch('sqlite3.connect')
@patch('services.stock_api.StockAPI.get_current_price', return_value=MOCK_PRICE)
@patch('services.database_service.DatabaseService.getStock')
def test_addStock(mock_fetch_stock, mock_fetch_price, mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_cursor
    mock_fetch_stock.return_value = 1

    assert DatabaseService.addStock("AAPL") == 1

    mock_fetch_price.assert_called_once_with("AAPL")
    mock_cursor.execute.assert_called_once_with('''
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
            ''', ("AAPL", "Apple Inc.", 100.0, "USD", 1000000000000, "Technology", "Consumer Electronics", "US"))

    mock_cursor.commit.assert_called_once()
    mock_fetch_stock.assert_called_once_with(symbol="AAPL")

@patch('sqlite3.connect')
@patch('services.stock_api.StockAPI.get_current_price', return_value=MOCK_PRICE)
@patch('services.database_service.DatabaseService.getStock')
@patch('logging.Logger.warning')
def test_addStock_already_in_database(mock_logger, mock_fetch_stock, mock_fetch_price, mock_connect, setup_database_service):
    DatabaseService.symbol_map = {"AAPL": 1}
    assert DatabaseService.addStock("AAPL") == 1

    mock_logger.assert_called_once()
    mock_fetch_price.assert_not_called()
    mock_connect.assert_not_called()
    mock_fetch_stock.assert_not_called()
    

@patch('sqlite3.connect')
def test_getStocks(mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cursor = MagicMock()
    mock_cursor.execute.return_value = [Stock(stockid=1, symbol='AAPL', name='Apple Inc.', price=150.0)]
    mock_conn.__enter__.return_value = mock_cursor
    DatabaseService.getStocks()

    assert DatabaseService.stocks[1].symbol == 'AAPL'
    assert DatabaseService.symbol_map['AAPL'] == 1

@patch('sqlite3.connect')
def test_getStock(mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cursor = MagicMock()
    mock_cursor.execute.return_value = [Stock(1, 'AAPL', 'Apple Inc.', 150.0)]
    mock_conn.__enter__.return_value = mock_cursor
    assert DatabaseService.getStock(symbol='AAPL') == 1

    assert DatabaseService.stocks[1].symbol == 'AAPL'
    assert DatabaseService.symbol_map['AAPL'] == 1

@patch('sqlite3.connect')
def test_getStock_zero_parameter(mock_connect, setup_database_service):

    assert DatabaseService.getStock() == -1

    mock_connect.assert_not_called()

@patch('sqlite3.connect')
@patch('logging.Logger.warning')
def test_getStock_two_parameters(mock_logger, mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cursor = MagicMock()
    mock_cursor.execute.return_value = [Stock(1, 'AAPL', 'Apple Inc.', 150.0)]
    mock_conn.__enter__.return_value = mock_cursor
    assert DatabaseService.getStock(symbol='AAPL', stockid=1) == 1

    mock_logger.assert_called_once()
    mock_cursor.execute.assert_called_once_with("SELECT * FROM mar__stocks WHERE stockid = ?", (1,))
    assert DatabaseService.stocks[1].symbol == 'AAPL'
    assert DatabaseService.symbol_map['AAPL'] == 1

@patch('sqlite3.connect')
@patch('services.stock_api.StockAPI.get_current_price', return_value=MOCK_PRICE)
def test_updateStocksPrice(mock_fetch_price, mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_cursor
    # Prepopulate the DatabaseService with one stock
    DatabaseService.stocks = {1: Stock(stockid=1, symbol='AAPL', price=150.0)}
    DatabaseService.symbol_map = {'AAPL': 1}

    DatabaseService.updateStocksPrice()

    mock_fetch_price.assert_called_once_with('AAPL')
    mock_cursor.execute.assert_called_once_with('UPDATE stocks SET price = ? WHERE stockid = ?', (100.0, 1))
    mock_cursor.commit.assert_called_once()
    assert DatabaseService.stocks[1].price == 100.0
    
@patch('services.stock_api.StockAPI.get_current_price', return_value=MOCK_PRICE)
@patch('sqlite3.connect')
@patch('logging.Logger.warning')
def test_updatePortfolioPositionsPrice(mock_logger_warning, mock_sqlite_connect, mock_fetch_real_time_price, setup_database_service):
    # Mock return values for the price fetching
    #mock_fetch_real_time_price.side_effect = lambda symbol: MOCK_PRICE["currentPrice"]
    
    # Mock SQLite connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_sqlite_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    
    # Mock positions with predefined stocks
    stock1 = Stock(stockid=1, symbol='AAPL', price=140.0)
    position1 = Position(stockid=1, quantity=10, stock=stock1)
    
    stock2 = Stock(stockid=2, symbol='GOOG', price=90.0)
    position2 = Position(stockid=2, quantity=5, stock=stock2)
    
    DatabaseService.positions = {1: position1, 2: position2}
    
    # Call the method under test
    DatabaseService.updatePortfolioPositionsPrice()
    
    # Check if the prices were updated correctly
    assert position1.stock.price == 100.0
    assert position2.stock.price == 100.0
    
    # Check if the database update was called with correct values
    mock_conn.execute.assert_any_call("UPDATE stocks SET price=?,name=?,currency=?,market_cap=?,sector=?,industry=?,country=?,logo_url=?,quote_type=? WHERE stockid=?", (100.0, "Apple Inc.", "USD", 1000000000000, "Technology", "Consumer Electronics", "US", "", "EQUITY", 1))
    mock_conn.execute.assert_any_call("UPDATE stocks SET price=?,name=?,currency=?,market_cap=?,sector=?,industry=?,country=?,logo_url=?,quote_type=? WHERE stockid=?", (100.0, "Apple Inc.", "USD", 1000000000000, "Technology", "Consumer Electronics", "US", "", "EQUITY", 2))
    assert mock_conn.execute.call_count == 2
    
    # Check if commit was called
    assert mock_conn.commit.call_count == 1

@patch('services.stock_api.StockAPI.get_current_price')
@patch('sqlite3.connect')
@patch('logging.Logger.warning')
def test_updatePortfolioPositionsPrice_no_positions(mock_logger_warning, mock_sqlite_connect, mock_fetch_real_time_price, setup_database_service):
    # Clear positions
    DatabaseService.positions = {}
    
    # Call the method under test
    DatabaseService.updatePortfolioPositionsPrice()
    
    # Check if the correct warning message was logged
    mock_logger_warning.assert_called_once_with("updatePortfolioPositionsPrice(): No position in the portfolio")
    
    # Check if fetch_real_time_price and database were not called
    assert mock_fetch_real_time_price.call_count == 0
    assert mock_sqlite_connect.call_count == 0

@patch('services.stock_api.StockAPI.get_current_price')
@patch('sqlite3.connect')
@patch('logging.Logger.warning')
def test_updatePortfolioPositionsPrice_no_stock_in_position(mock_logger_warning, mock_sqlite_connect, mock_fetch_real_time_price, setup_database_service):
    # Mock positions with one missing stock
    position1 = Position(stockid=1, quantity=10, stock=None)
    DatabaseService.positions = {1: position1}
    
    # Call the method under test
    DatabaseService.updatePortfolioPositionsPrice()
    
    # Check if the correct warning message was logged
    mock_logger_warning.assert_called_once_with("updatePortfolioPositionsPrice(): Position %d has no stock set. Skipping price update for this position", 1)
    
    # Check if fetch_real_time_price and database were not called
    assert mock_fetch_real_time_price.call_count == 0
    assert mock_sqlite_connect.call_count == 1

@patch('sqlite3.connect')
@patch('services.database_service.DatabaseService.getStock')
def test_getPositions(mock_getStock, mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cursor = MagicMock()
    mock_cursor.execute.return_value = [Position(stockid=1, quantity=10, distribution_real=5.0, distribution_target=10.0)]
    mock_conn.__enter__.return_value = mock_cursor
    DatabaseService.stocks = {1: Stock(stockid=1, symbol='AAPL', price=150.0)}
    DatabaseService.getPositions()

    mock_getStock.assert_not_called()
    assert len(DatabaseService.positions) == 1
    assert DatabaseService.positions[1].quantity == 10
    assert DatabaseService.positions[1].stock.stockid == 1

@patch('sqlite3.connect')
@patch('services.database_service.DatabaseService.getStock')
@patch('services.database_service.DatabaseService.stocks')
def test_getPositions_stock_in_database(mock_stocks_dict, mock_getStock, mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cursor = MagicMock()
    mock_cursor.execute.return_value = [Position(stockid=1, quantity=10, distribution_real=5.0, distribution_target=10.0)]
    mock_conn.__enter__.return_value = mock_cursor
    mock_values = {1: Stock(stockid=1, symbol='AAPL', price=150.0)}
    mock_stocks_dict.__getitem__.side_effect = mock_values.__getitem__
    mock_getStock.return_value = 1

    DatabaseService.getPositions()

    mock_getStock.assert_called_once()
    assert len(DatabaseService.positions) == 1
    assert DatabaseService.positions[1].quantity == 10
    assert DatabaseService.positions[1].stock.stockid == 1

@patch('sqlite3.connect')
@patch('services.database_service.DatabaseService.getStock')
@patch('logging.Logger.error')
def test_getPositions_stock_not_in_database(mock_logger, mock_getStock, mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cursor = MagicMock()
    mock_cursor.execute.return_value = [Position(stockid=1, quantity=10, distribution_real=5.0, distribution_target=10.0)]
    mock_conn.__enter__.return_value = mock_cursor
    mock_getStock.return_value = -1

    DatabaseService.getPositions()

    mock_logger.assert_called_once()
    mock_getStock.assert_called_once()
    assert len(DatabaseService.positions) == 1
    assert DatabaseService.positions[1].quantity == 10
    assert DatabaseService.positions[1].stock == None

@patch('sqlite3.connect')
@patch('services.database_service.DatabaseService.addStock')
@patch('services.database_service.DatabaseService.stocks')
def test_addPosition(mock_stocks_dict, mock_addStock, mock_connect, setup_database_service):
    mock_addStock.return_value = 1
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_cursor
    mock_values = {1: Stock(stockid=1, symbol='AAPL', price=150.0)}
    mock_stocks_dict.__getitem__.side_effect = mock_values.__getitem__
    DatabaseService.addPosition(symbol="AAPL", quantity=10, distribution_target=10.0)

    mock_addStock.assert_called_once_with(symbol="AAPL")
    mock_cursor.execute.assert_called_once()
    mock_cursor.commit.assert_called_once()
    assert 1 in DatabaseService.positions

@patch('sqlite3.connect')
@patch('services.database_service.DatabaseService.addStock')
@patch('logging.Logger.warning')
def test_addPosition_already_in_database(mock_logger, mock_addStock, mock_connect, setup_database_service):
    mock_addStock.return_value = 1
    DatabaseService.positions = {1: Position(stockid=1, quantity=10)}
    DatabaseService.addPosition(symbol="AAPL", quantity=10, distribution_target=10.0)

    mock_addStock.assert_called_once_with(symbol="AAPL")
    mock_logger.assert_called_once()
    mock_connect.assert_not_called()

@patch('sqlite3.connect')
@patch('logging.Logger.warning')
@patch('logging.Logger.debug')
def test_update_position(mock_logger_info, mock_logger_warning, mock_sqlite_connect, setup_database_service):
    # Mock DatabaseService.positions and symbol_map
    stock = Stock(stockid=1, symbol='AAPL', price=140.0)
    position = Position(stockid=1, quantity=10, distribution_target=20.0, distribution_real=15.0, stock=stock)
    DatabaseService.positions = {1: position}
    DatabaseService.symbol_map = {'AAPL': 1}
    
    # Mock SQLite connection and cursor
    mock_connection = MagicMock()
    mock_sqlite_connect.return_value.__enter__.return_value = mock_connection
    
    # Call the method under test
    DatabaseService.updatePosition('AAPL', quantity=15, distribution_target=25.0)
    
    # Check if the database update was called with correct values
    mock_connection.execute.assert_called_once_with(
        "UPDATE positions SET quantity = ?, distribution_target = ? WHERE stockid = ?", 
        [15, 25.0, 1]
    )
    mock_connection.commit.assert_called_once()
    
    # Check if the in-memory position was updated correctly
    assert position.quantity == 15
    assert position.distribution_target == 25.0
    
    # Check if the debug log was called
    mock_logger_info.assert_called_once_with(
        "updatePosition(): Position %s updated. Quantity: %s, Average cost basis: %s, Distribution target: %s, Distribution real: %s",
        'AAPL', 15, None, 25.0, 15.0
    )

@patch('sqlite3.connect')
@patch('logging.Logger.warning')
def test_update_position_symbol_not_in_portfolio(mock_logger_warning, mock_sqlite_connect, setup_database_service):
    # Mock DatabaseService.symbol_map to be empty
    DatabaseService.symbol_map = {}
    
    # Call the method under test
    DatabaseService.updatePosition('AAPL', quantity=15)
    
    # Check if the correct warning message was logged
    mock_logger_warning.assert_called_once_with("updatePosition(): Position %s not in the portfolio", 'AAPL')
    
    # Check if the database update was not called
    mock_sqlite_connect.assert_not_called()

@patch('sqlite3.connect')
@patch('logging.Logger.warning')
def test_update_position_no_fields_to_update(mock_logger_warning, mock_sqlite_connect, setup_database_service):
    # Mock DatabaseService.positions and symbol_map
    stock = Stock(stockid=1, symbol='AAPL', price=140.0)
    position = Position(stockid=1, quantity=10, distribution_target=20.0, distribution_real=15.0, stock=stock)
    DatabaseService.positions = {1: position}
    DatabaseService.symbol_map = {'AAPL': 1}
    
    # Call the method under test with no fields to update
    DatabaseService.updatePosition('AAPL')

    # Check if the correct warning message was logged
    mock_logger_warning.assert_called_once_with("updatePosition(): No fields to update for position %s", 'AAPL')

    # Check if the database update was not called
    mock_sqlite_connect.assert_not_called()


# --- getTransactions tests ---

@patch('sqlite3.connect')
def test_getTransactions_all(mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        (1, 1, 'AAPL', 10, 150.0, 'buy', '2024-01-15', 'Apple Inc.'),
        (2, 2, 'GOOGL', 5, 2000.0, 'buy', '2024-01-16', 'Alphabet Inc.'),
    ]

    result = DatabaseService.getTransactions()

    assert len(result) == 2
    assert result[0]['transactionid'] == 1
    assert result[0]['symbol'] == 'AAPL'
    assert result[1]['symbol'] == 'GOOGL'

    query = mock_conn.execute.call_args[0][0]
    assert 'WHERE' not in query
    assert 'LIMIT' in query


@patch('sqlite3.connect')
def test_getTransactions_filter_by_symbol(mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        (1, 1, 'AAPL', 10, 150.0, 'buy', '2024-01-15', 'Apple Inc.'),
    ]

    result = DatabaseService.getTransactions(symbol='aapl')

    assert len(result) == 1
    query = mock_conn.execute.call_args[0][0]
    params = mock_conn.execute.call_args[0][1]
    assert 'WHERE' in query
    assert 'AAPL' in params


@patch('sqlite3.connect')
def test_getTransactions_filter_by_type(mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    result = DatabaseService.getTransactions(transaction_type='SELL')

    query = mock_conn.execute.call_args[0][0]
    params = mock_conn.execute.call_args[0][1]
    assert 't.type = ?' in query
    assert 'sell' in params


@patch('sqlite3.connect')
def test_getTransactions_filter_both(mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    DatabaseService.getTransactions(symbol='AAPL', transaction_type='buy', limit=10)

    query = mock_conn.execute.call_args[0][0]
    params = mock_conn.execute.call_args[0][1]
    assert query.count('AND') == 1
    assert params == ['AAPL', 'buy', 10]


@patch('sqlite3.connect')
def test_getTransactions_empty(mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    result = DatabaseService.getTransactions()
    assert result == []


# --- getTransactionSummary tests ---

@patch('sqlite3.connect')
def test_getTransactionSummary_all(mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        ('AAPL', 'Apple Inc.', 5, 100, 10, 15000.0, 1500.0),
    ]

    result = DatabaseService.getTransactionSummary()

    assert len(result) == 1
    assert result[0]['symbol'] == 'AAPL'
    assert result[0]['transaction_count'] == 5
    assert result[0]['total_bought'] == 100
    assert result[0]['total_sold'] == 10
    assert result[0]['total_invested'] == 15000.0
    assert result[0]['total_divested'] == 1500.0
    assert result[0]['net_shares'] == 90
    assert result[0]['net_investment'] == 13500.0

    query = mock_conn.execute.call_args[0][0]
    assert 'WHERE' not in query


@patch('sqlite3.connect')
def test_getTransactionSummary_by_symbol(mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        ('AAPL', 'Apple Inc.', 5, 100, 10, 15000.0, 1500.0),
    ]

    result = DatabaseService.getTransactionSummary(symbol='aapl')

    query = mock_conn.execute.call_args[0][0]
    params = mock_conn.execute.call_args[0][1]
    assert 'WHERE' in query
    assert 'AAPL' in params


@patch('sqlite3.connect')
def test_getTransactionSummary_empty(mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    result = DatabaseService.getTransactionSummary()
    assert result == []


# --- getDeposits tests ---

@patch('sqlite3.connect')
def test_getDeposits(mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        (1, '2024-01-15', 1000.0, 1, 'EUR'),
        (2, '2024-02-15', 500.0, 1, 'EUR'),
    ]

    result = DatabaseService.getDeposits()

    assert len(result) == 2
    assert result[0]['depositid'] == 1
    assert result[0]['amount'] == 1000.0
    assert result[0]['currency'] == 'EUR'
    assert result[1]['depositid'] == 2

    params = mock_conn.execute.call_args[0][1]
    assert params == (100,)


@patch('sqlite3.connect')
def test_getDeposits_with_limit(mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    DatabaseService.getDeposits(limit=5)

    params = mock_conn.execute.call_args[0][1]
    assert params == (5,)


@patch('sqlite3.connect')
def test_getDeposits_null_currency_defaults_to_EUR(mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        (1, '2024-01-15', 1000.0, 1, None),
    ]

    result = DatabaseService.getDeposits()

    assert result[0]['currency'] == 'EUR'


@patch('sqlite3.connect')
def test_getDeposits_empty(mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    result = DatabaseService.getDeposits()
    assert result == []


# --- getTotalDeposits tests ---

@patch('sqlite3.connect')
def test_getTotalDeposits(mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (5000.555,)

    result = DatabaseService.getTotalDeposits()

    assert result == 5000.56


@patch('sqlite3.connect')
def test_getTotalDeposits_zero(mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (0,)

    result = DatabaseService.getTotalDeposits()

    assert result == 0.0


# --- addDeposit tests ---

@patch('sqlite3.connect')
def test_addDeposit(mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    mock_cursor.lastrowid = 42

    result = DatabaseService.addDeposit('2024-03-15', 2000.0)

    assert result['depositid'] == 42
    assert result['datestamp'] == '2024-03-15'
    assert result['amount'] == 2000.0
    assert result['portfolioid'] == 1
    assert result['currency'] == 'EUR'

    mock_conn.execute.assert_called_once()
    query = mock_conn.execute.call_args[0][0]
    assert 'INSERT INTO deposits' in query
    params = mock_conn.execute.call_args[0][1]
    assert params == ('2024-03-15', 2000.0)
    mock_conn.commit.assert_called_once()
