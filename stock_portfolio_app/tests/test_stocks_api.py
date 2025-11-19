import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

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
