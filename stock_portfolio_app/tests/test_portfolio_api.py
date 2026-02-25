import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch

from models.Stock import Stock
from models.Position import Position
from services.database_service import DatabaseService
from services.portfolio_service import PortfolioService

# Import the portfolio router
from api.routers import portfolio as portfolio_router


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
    """Create a minimal FastAPI app with portfolio router."""
    app = FastAPI()
    app.include_router(portfolio_router.router, prefix="/api/portfolio", tags=["portfolio"])
    return TestClient(app)


def test_get_portfolio_value_empty_portfolio():
    """Test getting portfolio value with no positions."""
    client = create_test_client()
    resp = client.get('/api/portfolio/value')
    assert resp.status_code == 200
    data = resp.json()
    assert data['total_value'] == 0
    assert data['currency'] == 'EUR'
    assert data['positions_count'] == 0


def test_get_portfolio_value_with_positions():
    """Test getting portfolio value with multiple positions."""
    stock1 = Stock(stockid=1, symbol='AAPL', name='Apple', price=150.0)
    stock2 = Stock(stockid=2, symbol='GOOGL', name='Google', price=2000.0)
    position1 = Position(stockid=1, quantity=10, stock=stock1)
    position2 = Position(stockid=2, quantity=5, stock=stock2)
    DatabaseService.positions = {1: position1, 2: position2}
    
    client = create_test_client()
    resp = client.get('/api/portfolio/value')
    assert resp.status_code == 200
    data = resp.json()
    assert data['total_value'] == 11500  # 10*150 + 5*2000
    assert data['positions_count'] == 2


def test_get_positions_empty():
    """Test getting positions when portfolio is empty."""
    client = create_test_client()
    resp = client.get('/api/portfolio/positions')
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_positions_with_data():
    """Test getting positions with stock data."""
    stock = Stock(
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
    position = Position(
        stockid=1, 
        quantity=10, 
        distribution_target=25.0,
        distribution_real=20.0,
        stock=stock
    )
    DatabaseService.positions = {1: position}
    
    client = create_test_client()
    resp = client.get('/api/portfolio/positions')
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]['stockid'] == 1
    assert data[0]['quantity'] == 10
    assert data[0]['distribution_target'] == 25.0
    assert data[0]['stock']['symbol'] == 'AAPL'
    assert data[0]['stock']['price'] == 150.0
    assert data[0]['delta'] == 5.0  # 25 - 20


def test_balance_portfolio_basic():
    """Test portfolio balancing with basic scenario."""
    stock1 = Stock(stockid=1, symbol='AAPL', name='Apple', price=100.0)
    stock2 = Stock(stockid=2, symbol='GOOGL', name='Google', price=200.0)
    position1 = Position(
        stockid=1, 
        quantity=10, 
        distribution_target=50.0,
        distribution_real=30.0,
        stock=stock1
    )
    position2 = Position(
        stockid=2, 
        quantity=5, 
        distribution_target=50.0,
        distribution_real=70.0,
        stock=stock2
    )
    DatabaseService.positions = {1: position1, 2: position2}
    
    client = create_test_client()
    resp = client.post('/api/portfolio/balance', json={
        'amount_to_buy': 1000,
        'min_amount_to_buy': 50
    })
    assert resp.status_code == 200
    data = resp.json()
    assert 'recommendations' in data
    assert 'leftover' in data
    assert 'total_invested' in data
    assert isinstance(data['recommendations'], list)


def test_balance_portfolio_insufficient_funds():
    """Test portfolio balancing with insufficient funds."""
    stock = Stock(stockid=1, symbol='AAPL', name='Apple', price=1000.0)
    position = Position(
        stockid=1,
        quantity=10,
        distribution_target=50.0,
        distribution_real=30.0,
        stock=stock
    )
    DatabaseService.positions = {1: position}
    
    client = create_test_client()
    resp = client.post('/api/portfolio/balance', json={
        'amount_to_buy': 500,  # Not enough to buy one share
        'min_amount_to_buy': 50
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data['recommendations']) == 0
    assert data['leftover'] == 500


def test_balance_portfolio_below_minimum():
    """Test that purchases below minimum are skipped."""
    stock = Stock(stockid=1, symbol='AAPL', name='Apple', price=100.0)
    position = Position(
        stockid=1,
        quantity=100,
        distribution_target=50.0,
        distribution_real=48.0,
        stock=stock
    )
    DatabaseService.positions = {1: position}
    
    client = create_test_client()
    resp = client.post('/api/portfolio/balance', json={
        'amount_to_buy': 150,
        'min_amount_to_buy': 200  # Minimum is higher than what we'd buy
    })
    assert resp.status_code == 200
    data = resp.json()
    # Should skip the purchase since it's below minimum
    assert data['leftover'] == 150


def test_get_distribution():
    """Test getting portfolio distribution."""
    stock1 = Stock(stockid=1, symbol='AAPL', name='Apple Inc.', price=150.0)
    stock2 = Stock(stockid=2, symbol='GOOGL', name='Alphabet Inc.', price=2000.0)
    position1 = Position(
        stockid=1,
        quantity=10,
        distribution_target=30.0,
        distribution_real=13.04,
        stock=stock1
    )
    position2 = Position(
        stockid=2,
        quantity=5,
        distribution_target=70.0,
        distribution_real=86.96,
        stock=stock2
    )
    DatabaseService.positions = {1: position1, 2: position2}
    
    client = create_test_client()
    resp = client.get('/api/portfolio/distribution')
    assert resp.status_code == 200
    data = resp.json()
    assert 'distributions' in data
    assert 'total_value' in data
    assert len(data['distributions']) == 2
    # Should be sorted by delta (descending)
    assert data['distributions'][0]['symbol'] in ['AAPL', 'GOOGL']
    assert 'delta' in data['distributions'][0]
    assert 'value' in data['distributions'][0]


def test_get_total_dividends(monkeypatch):
    """Test getting total yearly dividends."""
    stock = Stock(stockid=1, symbol='AAPL', name='Apple', price=150.0, dividend=0.92)
    position = Position(stockid=1, quantity=10, stock=stock)
    DatabaseService.positions = {1: position}
    
    def fake_get_total_dividend():
        return 100.50
    
    monkeypatch.setattr(PortfolioService, 'getDividendTotal', fake_get_total_dividend)
    
    client = create_test_client()
    resp = client.get('/api/portfolio/dividends/total')
    assert resp.status_code == 200
    data = resp.json()
    assert data['total_dividend'] == 100.50
    assert data['currency'] == 'EUR'


def test_get_dividends_breakdown(monkeypatch):
    """Test getting dividend breakdown by stock."""
    stock1 = Stock(stockid=1, symbol='AAPL', name='Apple Inc.', price=150.0)
    stock2 = Stock(stockid=2, symbol='MSFT', name='Microsoft Corp.', price=300.0)
    position1 = Position(stockid=1, quantity=10, stock=stock1)
    position2 = Position(stockid=2, quantity=5, stock=stock2)
    DatabaseService.positions = {1: position1, 2: position2}
    
    def fake_fetch_dividends(symbols):
        return {'AAPL': 0.92, 'MSFT': 2.72}
    
    monkeypatch.setattr('services.stock_api.StockAPI.get_current_year_dividends', fake_fetch_dividends)
    
    client = create_test_client()
    resp = client.get('/api/portfolio/dividends/breakdown')
    assert resp.status_code == 200
    data = resp.json()
    assert 'dividends' in data
    assert 'total_yearly_dividend' in data
    assert len(data['dividends']) == 2
    # Check first dividend entry
    assert data['dividends'][0]['symbol'] in ['AAPL', 'MSFT']
    assert 'dividend_rate' in data['dividends'][0]
    assert 'total_dividend' in data['dividends'][0]
    # Sorted by total_dividend descending, so MSFT should be first (2.72*5=13.6 > 0.92*10=9.2)
    assert data['dividends'][0]['symbol'] == 'MSFT'


def test_update_positions_prices(monkeypatch):
    """Test updating positions prices."""
    stock1 = Stock(stockid=1, symbol='AAPL', name='Apple', price=150.0)
    stock2 = Stock(stockid=2, symbol='GOOGL', name='Google', price=2000.0)
    position1 = Position(stockid=1, quantity=10, stock=stock1)
    position2 = Position(stockid=2, quantity=5, stock=stock2)
    DatabaseService.positions = {1: position1, 2: position2}
    
    called = {'count': 0}
    
    def fake_update_prices():
        called['count'] += 1
        # Simulate price updates
        stock1.price = 155.0
        stock2.price = 2100.0
    
    monkeypatch.setattr(DatabaseService, 'updatePortfolioPositionsPrice', classmethod(lambda cls: fake_update_prices()))
    
    client = create_test_client()
    resp = client.post('/api/portfolio/positions/update-prices')
    assert resp.status_code == 200
    data = resp.json()
    assert data['message'] == 'Position prices updated successfully'
    assert data['updated_count'] == 2
    assert called['count'] == 1


def test_get_positions_with_null_stock():
    """Test getting positions when a position has no stock attached."""
    position = Position(stockid=1, quantity=10, distribution_target=25.0, stock=None)
    DatabaseService.positions = {1: position}
    
    client = create_test_client()
    resp = client.get('/api/portfolio/positions')
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]['stock'] is None


def test_balance_portfolio_multiple_recommendations():
    """Test balancing with multiple stocks needing investment."""
    stock1 = Stock(stockid=1, symbol='AAPL', name='Apple', price=100.0)
    stock2 = Stock(stockid=2, symbol='MSFT', name='Microsoft', price=200.0)
    stock3 = Stock(stockid=3, symbol='GOOGL', name='Google', price=150.0)
    
    position1 = Position(
        stockid=1,
        quantity=5,
        distribution_target=40.0,
        distribution_real=20.0,
        stock=stock1
    )
    position2 = Position(
        stockid=2,
        quantity=3,
        distribution_target=30.0,
        distribution_real=25.0,
        stock=stock2
    )
    position3 = Position(
        stockid=3,
        quantity=2,
        distribution_target=30.0,
        distribution_real=15.0,
        stock=stock3
    )
    
    DatabaseService.positions = {1: position1, 2: position2, 3: position3}
    
    client = create_test_client()
    resp = client.post('/api/portfolio/balance', json={
        'amount_to_buy': 2000,
        'min_amount_to_buy': 50
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data['recommendations']) > 0
    assert data['total_invested'] > 0
    # Verify total invested doesn't exceed amount to buy
    assert data['total_invested'] <= 2000


def test_balance_portfolio_proportional_strategy():
    """Test proportional strategy allocates money by target percentages."""
    stock1 = Stock(stockid=1, symbol='AAPL', name='Apple', price=10.0)
    stock2 = Stock(stockid=2, symbol='MSFT', name='Microsoft', price=10.0)

    # Both stocks same price, different targets — real distribution doesn't matter
    position1 = Position(
        stockid=1, quantity=100, distribution_target=70.0,
        distribution_real=50.0, stock=stock1
    )
    position2 = Position(
        stockid=2, quantity=100, distribution_target=30.0,
        distribution_real=50.0, stock=stock2
    )
    DatabaseService.positions = {1: position1, 2: position2}

    client = create_test_client()
    resp = client.post('/api/portfolio/balance', json={
        'amount_to_buy': 1000,
        'min_amount_to_buy': 50,
        'strategy': 'proportional'
    })
    assert resp.status_code == 200
    data = resp.json()
    recs = {r['symbol']: r for r in data['recommendations']}
    # With equal stock prices of 10, AAPL should get 70% = 70 shares, MSFT 30% = 30 shares
    assert recs['AAPL']['shares'] == 70
    assert recs['MSFT']['shares'] == 30
    assert data['total_invested'] == 1000


def test_balance_portfolio_proportional_skips_below_minimum():
    """Test proportional strategy prunes positions below min_amount_to_buy
    and redistributes their share to remaining positions."""
    stock1 = Stock(stockid=1, symbol='AAPL', name='Apple', price=10.0)
    stock2 = Stock(stockid=2, symbol='MSFT', name='Microsoft', price=10.0)

    position1 = Position(
        stockid=1, quantity=10, distribution_target=90.0,
        distribution_real=50.0, stock=stock1
    )
    position2 = Position(
        stockid=2, quantity=10, distribution_target=10.0,
        distribution_real=50.0, stock=stock2
    )
    DatabaseService.positions = {1: position1, 2: position2}

    client = create_test_client()
    resp = client.post('/api/portfolio/balance', json={
        'amount_to_buy': 500,
        'min_amount_to_buy': 100,
        'strategy': 'proportional'
    })
    assert resp.status_code == 200
    data = resp.json()
    # AAPL (delta=40, highest priority) gets 90% of 500 = 450 → 45 shares
    # MSFT (delta=-40) gets 10% of remaining = 50, below min 100 → skipped
    assert len(data['recommendations']) == 1
    assert data['recommendations'][0]['symbol'] == 'AAPL'
    assert data['recommendations'][0]['shares'] == 45  # 90% of 500 / 10


def test_balance_portfolio_proportional_excludes_no_target():
    """Test that proportional strategy skips positions with no target."""
    stock1 = Stock(stockid=1, symbol='AAPL', name='Apple', price=10.0)
    stock2 = Stock(stockid=2, symbol='MSFT', name='Microsoft', price=10.0)

    position1 = Position(
        stockid=1, quantity=10, distribution_target=100.0,
        distribution_real=50.0, stock=stock1
    )
    position2 = Position(
        stockid=2, quantity=10, distribution_target=None,
        distribution_real=50.0, stock=stock2  # no target set
    )
    DatabaseService.positions = {1: position1, 2: position2}

    client = create_test_client()
    resp = client.post('/api/portfolio/balance', json={
        'amount_to_buy': 500,
        'min_amount_to_buy': 50,
        'strategy': 'proportional'
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data['recommendations']) == 1
    assert data['recommendations'][0]['symbol'] == 'AAPL'


def test_balance_portfolio_default_strategy_is_proportional():
    """Test that omitting strategy defaults to proportional behavior."""
    stock1 = Stock(stockid=1, symbol='AAPL', name='Apple', price=10.0)
    stock2 = Stock(stockid=2, symbol='MSFT', name='Microsoft', price=10.0)

    position1 = Position(
        stockid=1, quantity=10, distribution_target=60.0,
        distribution_real=50.0, stock=stock1
    )
    position2 = Position(
        stockid=2, quantity=10, distribution_target=40.0,
        distribution_real=50.0, stock=stock2
    )
    DatabaseService.positions = {1: position1, 2: position2}

    client = create_test_client()
    resp = client.post('/api/portfolio/balance', json={
        'amount_to_buy': 1000,
        'min_amount_to_buy': 50
    })
    assert resp.status_code == 200
    data = resp.json()
    recs = {r['symbol']: r for r in data['recommendations']}
    # Proportional: AAPL gets 60% = 60 shares, MSFT gets 40% = 40 shares
    assert recs['AAPL']['shares'] == 60
    assert recs['MSFT']['shares'] == 40

