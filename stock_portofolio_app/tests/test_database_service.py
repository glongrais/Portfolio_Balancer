
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict
from services.database_service import DatabaseService
from models.Stock import Stock

@pytest.fixture
def setup_database_service():
    # Reset the class variables before each test
    DatabaseService.symbol_map = {}
    DatabaseService.stocks = {}
    yield

@patch('sqlite3.connect')
@patch('services.data_processing.DataProcessing.fetch_real_time_price', return_value=100.0)
@patch('services.database_service.DatabaseService.getStock')
def test_addStock(mock_fetch_stock, mock_fetch_price, mock_connect, setup_database_service):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_cursor
    DatabaseService.addStock("AAPL")

    mock_fetch_price.assert_called_once_with("AAPL")
    mock_cursor.execute.assert_called_once_with('INSERT INTO stocks (symbol, price) VALUES (?, ?)', ("AAPL", 100.0,))
    mock_cursor.commit.assert_called_once()
    mock_fetch_stock.assert_called_once_with(symbol="AAPL")
    

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
    DatabaseService.getStock(symbol='AAPL')

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