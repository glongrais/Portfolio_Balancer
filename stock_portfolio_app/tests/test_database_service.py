
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict
from services.database_service import DatabaseService
from models.Stock import Stock
from models.Position import Position

@pytest.fixture
def setup_database_service():
    # Reset the class variables before each test
    DatabaseService.symbol_map = {}
    DatabaseService.stocks = {}
    DatabaseService.positions = {}
    yield

@patch('sqlite3.connect')
@patch('services.data_processing.DataProcessing.fetch_real_time_price', return_value=100.0)
@patch('services.database_service.DatabaseService.getStock')
def test_addStock(mock_fetch_stock, mock_fetch_price, mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_cursor
    mock_fetch_stock.return_value = 1

    assert DatabaseService.addStock("AAPL") == 1

    mock_fetch_price.assert_called_once_with("AAPL")
    mock_cursor.execute.assert_called_once_with('INSERT INTO stocks (symbol, price) VALUES (?, ?)', ("AAPL", 100.0,))
    mock_cursor.commit.assert_called_once()
    mock_fetch_stock.assert_called_once_with(symbol="AAPL")

@patch('sqlite3.connect')
@patch('services.data_processing.DataProcessing.fetch_real_time_price', return_value=100.0)
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
    mock_cursor.execute.assert_called_once_with("SELECT * FROM stocks WHERE stockid = ?", (1,))
    assert DatabaseService.stocks[1].symbol == 'AAPL'
    assert DatabaseService.symbol_map['AAPL'] == 1

@patch('sqlite3.connect')
@patch('services.data_processing.DataProcessing.fetch_real_time_price', return_value=100.0)
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
    
@patch('services.data_processing.DataProcessing.fetch_real_time_price')
@patch('sqlite3.connect')
@patch('logging.Logger.warning')
def test_updatePortfolioPositionsPrice(mock_logger_warning, mock_sqlite_connect, mock_fetch_real_time_price, setup_database_service):
    # Mock return values for the price fetching
    mock_fetch_real_time_price.side_effect = lambda symbol: {'AAPL': 150.0, 'GOOG': 100.0}[symbol]
    
    # Mock SQLite connection and cursor
    mock_connection = MagicMock()
    mock_cursor = MagicMock()
    mock_sqlite_connect.return_value.__enter__.return_value = mock_connection
    mock_connection.execute.return_value = mock_cursor
    
    # Mock positions with predefined stocks
    stock1 = Stock(stockid=1, symbol='AAPL', price=140.0)
    position1 = Position(stockid=1, quantity=10, stock=stock1)
    
    stock2 = Stock(stockid=2, symbol='GOOG', price=90.0)
    position2 = Position(stockid=2, quantity=5, stock=stock2)
    
    DatabaseService.positions = {1: position1, 2: position2}
    
    # Call the method under test
    DatabaseService.updatePortfolioPositionsPrice()
    
    # Check if the prices were updated correctly
    assert position1.stock.price == 150.0
    assert position2.stock.price == 100.0
    
    # Check if the database update was called with correct values
    mock_connection.execute.assert_any_call("UPDATE stocks SET price=? WHERE stockid=?", (150.0, 1))
    mock_connection.execute.assert_any_call("UPDATE stocks SET price=? WHERE stockid=?", (100.0, 2))
    assert mock_connection.execute.call_count == 2
    
    # Check if commit was called
    assert mock_connection.commit.call_count == 2

@patch('services.data_processing.DataProcessing.fetch_real_time_price')
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

@patch('services.data_processing.DataProcessing.fetch_real_time_price')
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
    assert mock_sqlite_connect.call_count == 0

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
