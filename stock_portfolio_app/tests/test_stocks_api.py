import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from models.Stock import Stock
from models.Position import Position
from services.database_service import DatabaseService

# Import the stocks router module and use its router for a lightweight test app
from api.routers import stocks as stocks_router


@pytest.fixture(autouse=True)
def reset_database_service():
    """Reset DatabaseService in-memory caches before each test."""
    DatabaseService.symbol_map = {}
    DatabaseService.stocks = {}
    DatabaseService.positions = {}
    yield
    # cleanup (not strictly necessary since we reset at start of fixture)
    DatabaseService.symbol_map = {}
    DatabaseService.stocks = {}
    DatabaseService.positions = {}


def create_test_client():
    """Create a minimal FastAPI app including only the stocks router to avoid app lifespan/startup logic."""
    app = FastAPI()
    app.include_router(stocks_router.router, prefix="/api/stocks", tags=["stocks"])
    return TestClient(app)


def test_get_all_stocks_returns_list():
    # prepare in-memory stock
    s = Stock(stockid=1, symbol='AAPL', name='Apple Inc.', price=150.0, currency='USD')
    DatabaseService.stocks = {1: s}
    DatabaseService.symbol_map = {'AAPL': 1}

    client = create_test_client()
    resp = client.get('/api/stocks/')
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]['symbol'] == 'AAPL'


def test_get_stock_by_symbol_found():
    s = Stock(stockid=2, symbol='MSFT', name='Microsoft Corp.', price=250.0, currency='USD')
    DatabaseService.stocks = {2: s}
    DatabaseService.symbol_map = {'MSFT': 2}

    client = create_test_client()
    resp = client.get('/api/stocks/MSFT')
    assert resp.status_code == 200
    data = resp.json()
    assert data['symbol'] == 'MSFT'
    assert data['price'] == 250.0


def test_get_stock_not_found_returns_404():
    client = create_test_client()
    resp = client.get('/api/stocks/UNKNOWN')
    assert resp.status_code == 404


def test_add_stock_existing_returns_existing_stock():
    s = Stock(stockid=3, symbol='NFLX', name='Netflix, Inc.', price=500.0, currency='USD')
    DatabaseService.stocks = {3: s}
    DatabaseService.symbol_map = {'NFLX': 3}

    client = create_test_client()
    resp = client.post('/api/stocks/', json={'symbol': 'nflx'})
    # endpoint decorator sets 201_CREATED; existing path returns the existing stock
    assert resp.status_code == 201
    data = resp.json()
    assert data['symbol'] == 'NFLX'
    assert data['stockid'] == 3


def test_update_prices_calls_service_and_returns_count(monkeypatch):
    # prepare some stocks
    s1 = Stock(stockid=4, symbol='BABA', price=80.0)
    s2 = Stock(stockid=5, symbol='TSLA', price=700.0)
    DatabaseService.stocks = {4: s1, 5: s2}
    DatabaseService.symbol_map = {'BABA': 4, 'TSLA': 5}

    called = {'count': 0}

    def fake_update_prices():
        # simulate updating prices
        called['count'] += 1
        for st in DatabaseService.stocks.values():
            st.price = st.price + 1.0

    monkeypatch.setattr(DatabaseService, 'updateStocksPrice', classmethod(lambda cls: fake_update_prices()))

    client = create_test_client()
    resp = client.post('/api/stocks/update-prices')
    assert resp.status_code == 200
    data = resp.json()
    assert data['message'] == 'Stock prices updated successfully'
    assert data['updated_count'] == 2


def test_add_position_creates_position(monkeypatch):
    # Monkeypatch addPosition so it doesn't touch the sqlite DB but updates in-memory structures
    def fake_add_position(symbol, quantity, distribution_target=None):
        # create a new stock and position in-memory
        stockid = max(DatabaseService.stocks.keys(), default=0) + 1
        stock = Stock(stockid=stockid, symbol=symbol, name=symbol, price=10.0)
        DatabaseService.stocks[stockid] = stock
        DatabaseService.symbol_map[symbol] = stockid
        pos = Position(stockid=stockid, quantity=quantity, distribution_target=distribution_target, stock=stock)
        DatabaseService.positions[stockid] = pos

    monkeypatch.setattr(DatabaseService, 'addPosition', classmethod(lambda cls, symbol, quantity, distribution_target=None: fake_add_position(symbol, quantity, distribution_target)))

    client = create_test_client()
    payload = {'symbol': 'NVDA', 'quantity': 5, 'distribution_target': 0.2}
    resp = client.post('/api/stocks/positions', json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data['quantity'] == 5
    assert data['distribution_target'] == 0.2
    assert data['stock']['symbol'] == 'NVDA'


def test_update_position_changes_values(monkeypatch):
    # prepare existing stock and position
    stock = Stock(stockid=10, symbol='AMZN', name='Amazon', price=3300.0)
    pos = Position(stockid=10, quantity=2, distribution_target=0.1, distribution_real=0.05, stock=stock)
    DatabaseService.stocks = {10: stock}
    DatabaseService.symbol_map = {'AMZN': 10}
    DatabaseService.positions = {10: pos}

    # Monkeypatch updatePosition to change the in-memory position
    def fake_update_position(symbol, quantity=None, distribution_target=None, distribution_real=None):
        sid = DatabaseService.symbol_map[symbol]
        p = DatabaseService.positions[sid]
        if quantity is not None:
            p.quantity = quantity
        if distribution_target is not None:
            p.distribution_target = distribution_target

    monkeypatch.setattr(DatabaseService, 'updatePosition', classmethod(lambda cls, symbol, quantity=None, distribution_target=None, distribution_real=None: fake_update_position(symbol, quantity, distribution_target, distribution_real)))

    client = create_test_client()
    payload = {'quantity': 4, 'distribution_target': 0.15}
    resp = client.put('/api/stocks/positions/AMZN', json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data['quantity'] == 4
    assert data['distribution_target'] == 0.15
    assert data['stock']['symbol'] == 'AMZN'


def test_get_all_stocks_empty_database():
    """Test getting all stocks when database is empty."""
    client = create_test_client()
    resp = client.get('/api/stocks/')
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_stock_case_insensitive():
    """Test that stock lookup is case insensitive."""
    s = Stock(stockid=1, symbol='AAPL', name='Apple Inc.', price=150.0, currency='USD')
    DatabaseService.stocks = {1: s}
    DatabaseService.symbol_map = {'AAPL': 1}
    
    client = create_test_client()
    # Use lowercase symbol
    resp = client.get('/api/stocks/aapl')
    assert resp.status_code == 200
    data = resp.json()
    assert data['symbol'] == 'AAPL'


def test_add_position_already_exists():
    """Test adding a position that already exists returns 400."""
    stock = Stock(stockid=1, symbol='TSLA', name='Tesla Inc.', price=700.0)
    position = Position(stockid=1, quantity=10, stock=stock)
    DatabaseService.stocks = {1: stock}
    DatabaseService.symbol_map = {'TSLA': 1}
    DatabaseService.positions = {1: position}
    
    client = create_test_client()
    payload = {'symbol': 'TSLA', 'quantity': 5, 'distribution_target': 0.2}
    resp = client.post('/api/stocks/positions', json=payload)
    assert resp.status_code == 400
    assert 'already exists' in resp.json()['detail']


def test_update_position_not_found():
    """Test updating a position that doesn't exist returns 404."""
    client = create_test_client()
    payload = {'quantity': 10, 'distribution_target': 0.2}
    resp = client.put('/api/stocks/positions/UNKNOWN', json=payload)
    assert resp.status_code == 404
    assert 'not found' in resp.json()['detail']


def test_update_position_stock_exists_but_no_position():
    """Test updating when stock exists but position doesn't."""
    stock = Stock(stockid=1, symbol='NFLX', name='Netflix', price=500.0)
    DatabaseService.stocks = {1: stock}
    DatabaseService.symbol_map = {'NFLX': 1}
    # No position created
    
    client = create_test_client()
    payload = {'quantity': 10}
    resp = client.put('/api/stocks/positions/NFLX', json=payload)
    assert resp.status_code == 404
    assert 'Position for NFLX not found' in resp.json()['detail']


def test_get_stock_returns_all_fields():
    """Test that stock response includes all expected fields."""
    s = Stock(
        stockid=1,
        symbol='AAPL',
        name='Apple Inc.',
        price=150.0,
        currency='USD',
        market_cap=2500000000000,
        sector='Technology',
        industry='Consumer Electronics',
        country='USA',
        dividend=0.92,
        dividend_yield=0.0061
    )
    DatabaseService.stocks = {1: s}
    DatabaseService.symbol_map = {'AAPL': 1}
    
    client = create_test_client()
    resp = client.get('/api/stocks/AAPL')
    assert resp.status_code == 200
    data = resp.json()
    assert data['stockid'] == 1
    assert data['symbol'] == 'AAPL'
    assert data['name'] == 'Apple Inc.'
    assert data['price'] == 150.0
    assert data['currency'] == 'USD'
    assert data['market_cap'] == 2500000000000
    assert data['sector'] == 'Technology'
    assert data['industry'] == 'Consumer Electronics'
    assert data['country'] == 'USA'
    assert data['dividend'] == 0.92
    assert data['dividend_yield'] == 0.0061


def test_add_position_includes_all_stock_fields():
    """Test that adding a position returns all stock fields."""
    def fake_add_position(symbol, quantity, distribution_target=None):
        stockid = 1
        stock = Stock(
            stockid=stockid,
            symbol=symbol,
            name='Test Company',
            price=100.0,
            currency='USD',
            market_cap=1000000000,
            sector='Tech',
            industry='Software',
            country='USA',
            dividend=1.0,
            dividend_yield=0.01
        )
        DatabaseService.stocks[stockid] = stock
        DatabaseService.symbol_map[symbol] = stockid
        pos = Position(
            stockid=stockid,
            quantity=quantity,
            distribution_target=distribution_target,
            stock=stock
        )
        DatabaseService.positions[stockid] = pos
    
    # Use monkeypatch fixture properly
    import unittest.mock
    with unittest.mock.patch.object(DatabaseService, 'addPosition', classmethod(lambda cls, symbol, quantity, distribution_target=None: fake_add_position(symbol, quantity, distribution_target))):
        client = create_test_client()
        payload = {'symbol': 'TEST', 'quantity': 10, 'distribution_target': 0.25}
        resp = client.post('/api/stocks/positions', json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert 'stock' in data
        assert data['stock']['symbol'] == 'TEST'
        assert data['stock']['sector'] == 'Tech'
        assert data['stock']['dividend'] == 1.0


def test_position_response_includes_delta():
    """Test that position response includes calculated delta."""
    stock = Stock(stockid=1, symbol='AAPL', name='Apple', price=150.0)
    position = Position(
        stockid=1,
        quantity=10,
        distribution_target=30.0,
        distribution_real=20.0,
        stock=stock
    )
    
    def fake_add_position(symbol, quantity, distribution_target=None):
        DatabaseService.stocks[1] = stock
        DatabaseService.symbol_map[symbol] = 1
        DatabaseService.positions[1] = position
    
    import unittest.mock
    with unittest.mock.patch.object(DatabaseService, 'addPosition', classmethod(lambda cls, symbol, quantity, distribution_target=None: fake_add_position(symbol, quantity, distribution_target))):
        client = create_test_client()
        payload = {'symbol': 'AAPL', 'quantity': 10, 'distribution_target': 30.0}
        resp = client.post('/api/stocks/positions', json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert 'delta' in data
        assert data['delta'] == 10.0  # 30 - 20


def test_update_position_partial_update():
    """Test updating only quantity without changing target."""
    stock = Stock(stockid=1, symbol='MSFT', name='Microsoft', price=300.0)
    pos = Position(
        stockid=1,
        quantity=5,
        distribution_target=0.2,
        distribution_real=0.15,
        stock=stock
    )
    DatabaseService.stocks = {1: stock}
    DatabaseService.symbol_map = {'MSFT': 1}
    DatabaseService.positions = {1: pos}
    
    def fake_update_position(symbol, quantity=None, distribution_target=None, distribution_real=None):
        sid = DatabaseService.symbol_map[symbol]
        p = DatabaseService.positions[sid]
        if quantity is not None:
            p.quantity = quantity
        if distribution_target is not None:
            p.distribution_target = distribution_target
    
    import unittest.mock
    with unittest.mock.patch.object(DatabaseService, 'updatePosition', classmethod(lambda cls, symbol, quantity=None, distribution_target=None, distribution_real=None: fake_update_position(symbol, quantity, distribution_target, distribution_real))):
        client = create_test_client()
        # Only update quantity
        payload = {'quantity': 10}
        resp = client.put('/api/stocks/positions/MSFT', json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data['quantity'] == 10
        assert data['distribution_target'] == 0.2  # Unchanged


# --- Price History Endpoint Tests ---

@patch('services.database_service.DatabaseService.getStockPriceHistory')
def test_get_stock_price_history(mock_get_history):
    """Test getting price history for a stock."""
    s = Stock(stockid=1, symbol='AAPL', name='Apple Inc.', price=150.0, currency='USD')
    DatabaseService.stocks = {1: s}
    DatabaseService.symbol_map = {'AAPL': 1}

    mock_get_history.return_value = [
        {"datestamp": "2024-01-15", "closeprice": 185.92},
        {"datestamp": "2024-01-16", "closeprice": 187.44},
    ]

    client = create_test_client()
    resp = client.get('/api/stocks/AAPL/price-history')

    assert resp.status_code == 200
    data = resp.json()
    assert data['symbol'] == 'AAPL'
    assert data['name'] == 'Apple Inc.'
    assert data['currency'] == 'USD'
    assert len(data['data']) == 2
    assert data['data'][0]['datestamp'] == '2024-01-15'
    assert data['data'][0]['closeprice'] == 185.92
    mock_get_history.assert_called_once_with('AAPL', None, None)


@patch('services.database_service.DatabaseService.getStockPriceHistory')
def test_get_stock_price_history_with_date_range(mock_get_history):
    """Test getting price history with date filters."""
    s = Stock(stockid=1, symbol='AAPL', name='Apple Inc.', price=150.0, currency='USD')
    DatabaseService.stocks = {1: s}
    DatabaseService.symbol_map = {'AAPL': 1}

    mock_get_history.return_value = [
        {"datestamp": "2024-06-01", "closeprice": 190.0},
    ]

    client = create_test_client()
    resp = client.get('/api/stocks/AAPL/price-history?start_date=2024-06-01&end_date=2024-06-30')

    assert resp.status_code == 200
    mock_get_history.assert_called_once_with('AAPL', '2024-06-01', '2024-06-30')


def test_get_stock_price_history_not_found():
    """Test price history for unknown stock returns 404."""
    client = create_test_client()
    resp = client.get('/api/stocks/UNKNOWN/price-history')
    assert resp.status_code == 404


@patch('services.database_service.DatabaseService.getStockPriceHistory')
def test_get_stock_price_history_empty(mock_get_history):
    """Test price history when no data exists."""
    s = Stock(stockid=1, symbol='AAPL', name='Apple Inc.', price=150.0, currency='USD')
    DatabaseService.stocks = {1: s}
    DatabaseService.symbol_map = {'AAPL': 1}

    mock_get_history.return_value = []

    client = create_test_client()
    resp = client.get('/api/stocks/AAPL/price-history')

    assert resp.status_code == 200
    data = resp.json()
    assert data['symbol'] == 'AAPL'
    assert len(data['data']) == 0


@patch('services.database_service.DatabaseService.getStockPriceHistory')
def test_get_stock_price_history_case_insensitive(mock_get_history):
    """Test that price history lookup is case insensitive."""
    s = Stock(stockid=1, symbol='AAPL', name='Apple Inc.', price=150.0, currency='USD')
    DatabaseService.stocks = {1: s}
    DatabaseService.symbol_map = {'AAPL': 1}

    mock_get_history.return_value = []

    client = create_test_client()
    resp = client.get('/api/stocks/aapl/price-history')

    assert resp.status_code == 200
    mock_get_history.assert_called_once_with('AAPL', None, None)


@patch('services.database_service.DatabaseService.getStockPriceHistory')
def test_get_stock_price_history_error(mock_get_history):
    """Test error handling for price history."""
    s = Stock(stockid=1, symbol='AAPL', name='Apple Inc.', price=150.0, currency='USD')
    DatabaseService.stocks = {1: s}
    DatabaseService.symbol_map = {'AAPL': 1}

    mock_get_history.side_effect = Exception("Database error")

    client = create_test_client()
    resp = client.get('/api/stocks/AAPL/price-history')

    assert resp.status_code == 500
    assert 'Failed to fetch price history' in resp.json()['detail']
