import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sqlite3

from services.database_service import DatabaseService

# Import the transactions router
from api.routers import transactions as transactions_router


@pytest.fixture(autouse=True)
def reset_database_service():
    """Reset DatabaseService in-memory caches before each test."""
    DatabaseService.symbol_map = {}
    DatabaseService.stocks = {}
    DatabaseService.positions = {}
    yield
    DatabaseService.symbol_map = {}
    DatabaseService.stocks = {}
    DatabaseService.positions = {}


def create_test_client():
    """Create a minimal FastAPI app with transactions router."""
    app = FastAPI()
    app.include_router(transactions_router.router, prefix="/api/transactions", tags=["transactions"])
    return TestClient(app)


@patch('sqlite3.connect')
def test_get_transactions_all(mock_connect):
    """Test getting all transactions without filters."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    
    # Mock transaction data (8 columns: transactionid, stockid, symbol, quantity, price, type, datestamp, name)
    mock_cursor.fetchall.return_value = [
        (1, 1, 'AAPL', 10, 150.0, 'buy', '2024-01-15', 'Apple Inc.'),
        (2, 2, 'GOOGL', 5, 2000.0, 'buy', '2024-01-16', 'Alphabet Inc.'),
    ]
    
    client = create_test_client()
    resp = client.get('/api/transactions/')
    
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]['transactionid'] == 1
    assert data[0]['symbol'] == 'AAPL'
    assert data[0]['quantity'] == 10
    assert data[0]['type'] == 'buy'


@patch('sqlite3.connect')
def test_get_transactions_filter_by_symbol(mock_connect):
    """Test getting transactions filtered by symbol."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    
    mock_cursor.fetchall.return_value = [
        (1, 1, 'AAPL', 10, 150.0, 'buy', '2024-01-15', 'Apple Inc.'),
    ]

    client = create_test_client()
    resp = client.get('/api/transactions/?symbol=AAPL')
    
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]['symbol'] == 'AAPL'
    
    # Verify the query was called with correct parameters
    call_args = mock_conn.execute.call_args
    assert 'WHERE' in call_args[0][0]
    assert 'AAPL' in call_args[0][1]


@patch('sqlite3.connect')
def test_get_transactions_filter_by_type(mock_connect):
    """Test getting transactions filtered by type."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    
    mock_cursor.fetchall.return_value = [
        (2, 1, 'AAPL', 5, 155.0, 'sell', '2024-01-20', 'Apple Inc.'),
    ]

    client = create_test_client()
    resp = client.get('/api/transactions/?transaction_type=sell')
    
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]['type'] == 'sell'


@patch('sqlite3.connect')
def test_get_transactions_filter_by_both(mock_connect):
    """Test getting transactions filtered by symbol and type."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    
    mock_cursor.fetchall.return_value = [
        (2, 1, 'AAPL', 5, 155.0, 'sell', '2024-01-20', 'Apple Inc.'),
    ]

    client = create_test_client()
    resp = client.get('/api/transactions/?symbol=AAPL&transaction_type=sell')
    
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    
    # Verify both conditions are in the query
    call_args = mock_conn.execute.call_args
    query = call_args[0][0]
    assert query.count('WHERE') == 1
    assert query.count('AND') == 1


@patch('sqlite3.connect')
def test_get_transactions_with_limit(mock_connect):
    """Test getting transactions with custom limit."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    
    mock_cursor.fetchall.return_value = [(i, 1, 'AAPL', 1, 150.0, 'buy', f'2024-01-{i:02d}', 'Apple Inc.') for i in range(1, 11)]
    
    client = create_test_client()
    resp = client.get('/api/transactions/?limit=10')
    
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 10
    
    # Verify limit is in the query
    call_args = mock_conn.execute.call_args
    assert 'LIMIT' in call_args[0][0]
    assert 10 in call_args[0][1]


@patch('sqlite3.connect')
def test_get_transactions_empty_result(mock_connect):
    """Test getting transactions when no transactions exist."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    
    mock_cursor.fetchall.return_value = []
    
    client = create_test_client()
    resp = client.get('/api/transactions/')
    
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 0


@patch('services.database_service.DatabaseService.upsertTransactions')
def test_add_transaction_buy(mock_upsert):
    """Test adding a buy transaction."""
    from datetime import datetime
    client = create_test_client()
    
    transaction_data = {
        'date': '2024-01-15',
        'rowid': 123,
        'type': 'buy',
        'symbol': 'AAPL',
        'quantity': 10,
        'price': 150.0
    }
    
    resp = client.post('/api/transactions/', json=transaction_data)
    
    assert resp.status_code == 201
    data = resp.json()
    assert data['message'] == 'Transaction added successfully'
    assert data['symbol'] == 'AAPL'
    assert data['type'] == 'buy'
    assert data['quantity'] == 10
    assert data['price'] == 150.0
    
    # Verify upsertTransactions was called
    mock_upsert.assert_called_once()
    call_kwargs = mock_upsert.call_args[1]
    assert call_kwargs['rowid'] == 123
    assert call_kwargs['type'] == 'buy'
    assert call_kwargs['symbol'] == 'AAPL'
    assert call_kwargs['quantity'] == 10
    assert call_kwargs['price'] == 150.0
    # Date is converted to datetime object by Pydantic
    assert isinstance(call_kwargs['date'], datetime)


@patch('services.database_service.DatabaseService.upsertTransactions')
def test_add_transaction_sell(mock_upsert):
    """Test adding a sell transaction."""
    client = create_test_client()
    
    transaction_data = {
        'date': '2024-01-20',
        'rowid': 124,
        'type': 'sell',
        'symbol': 'MSFT',
        'quantity': 5,
        'price': 300.0
    }
    
    resp = client.post('/api/transactions/', json=transaction_data)
    
    assert resp.status_code == 201
    data = resp.json()
    assert data['message'] == 'Transaction added successfully'
    assert data['symbol'] == 'MSFT'
    assert data['type'] == 'sell'


@patch('services.database_service.DatabaseService.upsertTransactions')
def test_add_transaction_case_insensitive(mock_upsert):
    """Test that symbol is converted to uppercase."""
    client = create_test_client()
    
    transaction_data = {
        'date': '2024-01-15',
        'rowid': 125,
        'type': 'buy',
        'symbol': 'aapl',
        'quantity': 10,
        'price': 150.0
    }

    resp = client.post('/api/transactions/', json=transaction_data)

    assert resp.status_code == 201
    data = resp.json()
    assert data['symbol'] == 'AAPL'

    # Verify uppercase symbol passed to service
    mock_upsert.assert_called_once()
    call_kwargs = mock_upsert.call_args[1]
    assert call_kwargs['symbol'] == 'AAPL'
    assert call_kwargs['type'] == 'buy'


@patch('sqlite3.connect')
def test_get_transaction_summary_all(mock_connect):
    """Test getting transaction summary for all stocks."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    
    mock_cursor.fetchall.return_value = [
        ('AAPL', 'Apple Inc.', 5, 100, 10, 15000.0, 1500.0),
        ('GOOGL', 'Alphabet Inc.', 3, 50, 5, 100000.0, 10000.0),
    ]
    
    client = create_test_client()
    resp = client.get('/api/transactions/summary')
    
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    
    # Check first stock
    assert data[0]['symbol'] == 'AAPL'
    assert data[0]['name'] == 'Apple Inc.'
    assert data[0]['transaction_count'] == 5
    assert data[0]['total_bought'] == 100
    assert data[0]['total_sold'] == 10
    assert data[0]['total_invested'] == 15000.0
    assert data[0]['total_divested'] == 1500.0
    assert data[0]['net_shares'] == 90
    assert data[0]['net_investment'] == 13500.0


@patch('sqlite3.connect')
def test_get_transaction_summary_by_symbol(mock_connect):
    """Test getting transaction summary filtered by symbol."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    
    mock_cursor.fetchall.return_value = [
        ('AAPL', 'Apple Inc.', 5, 100, 10, 15000.0, 1500.0),
    ]
    
    client = create_test_client()
    resp = client.get('/api/transactions/summary?symbol=AAPL')
    
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]['symbol'] == 'AAPL'
    
    # Verify the query includes WHERE clause
    call_args = mock_conn.execute.call_args
    assert 'WHERE' in call_args[0][0]
    assert 'AAPL' in call_args[0][1]


@patch('sqlite3.connect')
def test_get_transaction_summary_empty(mock_connect):
    """Test getting transaction summary when no transactions exist."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    
    mock_cursor.fetchall.return_value = []
    
    client = create_test_client()
    resp = client.get('/api/transactions/summary')
    
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 0


@patch('services.database_service.DatabaseService.upsertTransactions')
def test_add_transaction_error_handling(mock_upsert):
    """Test error handling when adding transaction fails."""
    mock_upsert.side_effect = Exception('Database error')
    
    client = create_test_client()
    
    transaction_data = {
        'date': '2024-01-15',
        'rowid': 126,
        'type': 'buy',
        'symbol': 'AAPL',
        'quantity': 10,
        'price': 150.0
    }
    
    resp = client.post('/api/transactions/', json=transaction_data)
    
    assert resp.status_code == 500
    assert 'Failed to add transaction' in resp.json()['detail']


@patch('sqlite3.connect')
def test_get_transactions_error_handling(mock_connect):
    """Test error handling when fetching transactions fails."""
    mock_connect.side_effect = Exception('Database connection error')
    
    client = create_test_client()
    resp = client.get('/api/transactions/')
    
    assert resp.status_code == 500
    assert 'Failed to fetch transactions' in resp.json()['detail']


@patch('sqlite3.connect')
def test_get_summary_error_handling(mock_connect):
    """Test error handling when fetching summary fails."""
    mock_connect.side_effect = Exception('Database error')
    
    client = create_test_client()
    resp = client.get('/api/transactions/summary')
    
    assert resp.status_code == 500
    assert 'Failed to fetch transaction summary' in resp.json()['detail']


@patch('sqlite3.connect')
def test_get_transactions_with_max_limit(mock_connect):
    """Test that limit is capped at maximum value."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []
    
    client = create_test_client()
    # Try to request more than max limit (1000)
    resp = client.get('/api/transactions/?limit=1000')
    
    assert resp.status_code == 200
    
    # Verify limit parameter in query
    call_args = mock_conn.execute.call_args
    params = call_args[0][1]
    assert params[-1] == 1000  # Last parameter should be the limit


# --- Sell validation tests ---

@patch('services.database_service.DatabaseService.upsertTransactions')
def test_add_sell_transaction_exceeding_held_returns_400(mock_upsert):
    """Test that selling more shares than held returns 400."""
    mock_upsert.side_effect = ValueError('Cannot sell 10 shares of AAPL: only 5 shares held')

    client = create_test_client()

    transaction_data = {
        'date': '2024-01-20',
        'rowid': 200,
        'type': 'sell',
        'symbol': 'AAPL',
        'quantity': 10,
        'price': 155.0
    }

    resp = client.post('/api/transactions/', json=transaction_data)

    assert resp.status_code == 400
    assert 'Cannot sell' in resp.json()['detail']

