import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from models.Stock import Stock
from models.Position import Position
from services.database_service import DatabaseService
from api.routers import crypto as crypto_router


@pytest.fixture(autouse=True)
def reset_database_service():
    """Reset DatabaseService in-memory caches before each test."""
    DatabaseService.symbol_map = {}
    DatabaseService.stocks = {}
    DatabaseService.positions = {}
    DatabaseService._crypto_portfolio_id = None
    yield
    DatabaseService.symbol_map = {}
    DatabaseService.stocks = {}
    DatabaseService.positions = {}
    DatabaseService._crypto_portfolio_id = None


def create_crypto_client():
    app = FastAPI()
    app.include_router(crypto_router.router, prefix="/api/crypto", tags=["crypto"])
    return TestClient(app)


SAMPLE_BTC_STOCK = Stock(
    stockid=100, name="Bitcoin USD", symbol="BTC-USD", price=95000.0,
    currency="USD", market_cap=None, sector="", industry="", country="",
    logo_url="", quote_type="CRYPTOCURRENCY", ex_dividend_date=None,
)

SAMPLE_ETH_STOCK = Stock(
    stockid=101, name="Ethereum USD", symbol="ETH-USD", price=3500.0,
    currency="USD", market_cap=None, sector="", industry="", country="",
    logo_url="", quote_type="CRYPTOCURRENCY", ex_dividend_date=None,
)


def setup_crypto_positions():
    """Helper to set up crypto portfolio state."""
    DatabaseService._crypto_portfolio_id = 99
    DatabaseService.stocks[100] = SAMPLE_BTC_STOCK
    DatabaseService.stocks[101] = SAMPLE_ETH_STOCK
    DatabaseService.symbol_map["BTC-USD"] = 100
    DatabaseService.symbol_map["ETH-USD"] = 101
    DatabaseService.positions[99] = {
        100: Position(stockid=100, quantity=0.5, average_cost_basis=60000.0,
                      stock=SAMPLE_BTC_STOCK, portfolio_id=99),
        101: Position(stockid=101, quantity=2.0, average_cost_basis=2000.0,
                      stock=SAMPLE_ETH_STOCK, portfolio_id=99),
    }


# ── Holdings tests ──────────────────────────────────────────────

@patch('services.stock_api.StockAPI.get_fx_rate')
@patch('services.database_service.DatabaseService.getCryptoPortfolioId')
def test_get_holdings(mock_portfolio_id, mock_fx):
    setup_crypto_positions()
    mock_portfolio_id.return_value = 99
    mock_fx.return_value = 0.92
    client = create_crypto_client()
    resp = client.get('/api/crypto/holdings')
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    btc = next(h for h in data if h['symbol'] == 'BTC-USD')
    assert btc['quantity'] == 0.5
    assert btc['current_price'] == 95000.0
    assert btc['value'] == 47500.0
    assert btc['gain_loss'] is not None


@patch('services.database_service.DatabaseService.getCryptoPortfolioId')
def test_get_holdings_empty(mock_portfolio_id):
    mock_portfolio_id.return_value = 99
    client = create_crypto_client()
    resp = client.get('/api/crypto/holdings')
    assert resp.status_code == 200
    assert resp.json() == []


@patch('services.stock_api.StockAPI.get_fx_rate')
@patch('services.database_service.DatabaseService.addPosition')
@patch('services.database_service.DatabaseService.addStock')
@patch('services.database_service.DatabaseService.getCryptoPortfolioId')
def test_add_holding(mock_portfolio_id, mock_add_stock, mock_add_pos, mock_fx):
    mock_portfolio_id.return_value = 99
    mock_add_stock.return_value = 100
    mock_fx.return_value = 0.92

    # After addStock, the stock should be in cache
    DatabaseService.stocks[100] = SAMPLE_BTC_STOCK
    DatabaseService.symbol_map["BTC-USD"] = 100
    # After addPosition, position should be in cache
    DatabaseService.positions[99] = {
        100: Position(stockid=100, quantity=0.5, average_cost_basis=None,
                      stock=SAMPLE_BTC_STOCK, portfolio_id=99),
    }

    client = create_crypto_client()
    resp = client.post('/api/crypto/holdings', json={
        "symbol": "BTC-USD",
        "quantity": 0.5,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data['symbol'] == 'BTC-USD'
    assert data['quantity'] == 0.5


@patch('services.database_service.DatabaseService.addStock')
@patch('services.database_service.DatabaseService.getCryptoPortfolioId')
def test_add_holding_not_crypto(mock_portfolio_id, mock_add_stock):
    mock_portfolio_id.return_value = 99
    mock_add_stock.return_value = 200
    # Set up a non-crypto stock
    aapl = Stock(
        stockid=200, name="Apple Inc.", symbol="AAPL", price=180.0,
        currency="USD", market_cap=None, sector="Technology", industry="",
        country="US", logo_url="", quote_type="EQUITY", ex_dividend_date=None,
    )
    DatabaseService.stocks[200] = aapl
    DatabaseService.symbol_map["AAPL"] = 200

    client = create_crypto_client()
    resp = client.post('/api/crypto/holdings', json={
        "symbol": "AAPL",
        "quantity": 10,
    })
    assert resp.status_code == 400
    assert 'not a cryptocurrency' in resp.json()['detail']


@patch('services.stock_api.StockAPI.get_fx_rate')
@patch('services.database_service.DatabaseService.removePosition')
@patch('services.database_service.DatabaseService.getCryptoPortfolioId')
def test_delete_holding(mock_portfolio_id, mock_remove, mock_fx):
    mock_portfolio_id.return_value = 99
    mock_remove.return_value = None
    client = create_crypto_client()
    resp = client.delete('/api/crypto/holdings/BTC-USD')
    assert resp.status_code == 204
    mock_remove.assert_called_once_with("BTC-USD", portfolio_id=99)


# ── Summary tests ───────────────────────────────────────────────

@patch('services.database_service.DatabaseService.getCryptoSummary')
def test_get_summary(mock_summary):
    mock_summary.return_value = {
        "total_value": 50000.0,
        "total_cost_basis": 35000.0,
        "total_gain_loss": 15000.0,
        "total_gain_loss_pct": 42.86,
        "holdings_count": 2,
    }
    client = create_crypto_client()
    resp = client.get('/api/crypto/summary')
    assert resp.status_code == 200
    data = resp.json()
    assert data['total_value'] == 50000.0
    assert data['holdings_count'] == 2
    assert data['total_gain_loss_pct'] == 42.86


@patch('services.database_service.DatabaseService.getCryptoSummary')
def test_get_summary_empty(mock_summary):
    mock_summary.return_value = {
        "total_value": 0.0,
        "total_cost_basis": 0.0,
        "total_gain_loss": 0.0,
        "total_gain_loss_pct": 0.0,
        "holdings_count": 0,
    }
    client = create_crypto_client()
    resp = client.get('/api/crypto/summary')
    assert resp.status_code == 200
    assert resp.json()['holdings_count'] == 0


# ── Transaction tests ───────────────────────────────────────────

@patch('services.database_service.DatabaseService.getTransactions')
@patch('services.database_service.DatabaseService.getCryptoPortfolioId')
def test_get_transactions(mock_portfolio_id, mock_txns):
    mock_portfolio_id.return_value = 99
    mock_txns.return_value = [{
        "transactionid": 1, "stockid": 100, "symbol": "BTC-USD",
        "quantity": 0.5, "price": 60000.0, "type": "BUY",
        "datestamp": "2025-06-01", "name": "Bitcoin USD",
    }]
    client = create_crypto_client()
    resp = client.get('/api/crypto/transactions')
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]['symbol'] == 'BTC-USD'


@patch('services.database_service.DatabaseService.upsertTransactions')
@patch('services.database_service.DatabaseService.getCryptoPortfolioId')
def test_add_staking_transaction(mock_portfolio_id, mock_upsert):
    mock_portfolio_id.return_value = 99
    mock_upsert.return_value = None

    # Set up BTC as a crypto stock in cache
    DatabaseService.stocks[100] = SAMPLE_BTC_STOCK
    DatabaseService.symbol_map["BTC-USD"] = 100

    client = create_crypto_client()
    resp = client.post('/api/crypto/transactions', json={
        "symbol": "BTC-USD",
        "quantity": 0.001,
        "price": 95000.0,
        "type": "STAKING",
        "date": "2026-03-04",
    })
    assert resp.status_code == 201
    assert 'STAKING' in resp.json()['message']


@patch('services.database_service.DatabaseService.getCryptoPortfolioId')
def test_add_transaction_not_crypto(mock_portfolio_id):
    mock_portfolio_id.return_value = 99
    aapl = Stock(
        stockid=200, name="Apple Inc.", symbol="AAPL", price=180.0,
        currency="USD", market_cap=None, sector="Technology", industry="",
        country="US", logo_url="", quote_type="EQUITY", ex_dividend_date=None,
    )
    DatabaseService.stocks[200] = aapl
    DatabaseService.symbol_map["AAPL"] = 200

    client = create_crypto_client()
    resp = client.post('/api/crypto/transactions', json={
        "symbol": "AAPL",
        "quantity": 1,
        "price": 180.0,
        "type": "BUY",
        "date": "2026-03-04",
    })
    assert resp.status_code == 400
    assert 'not a cryptocurrency' in resp.json()['detail']


# ── History tests ───────────────────────────────────────────────

@patch('services.database_service.DatabaseService.getFxRateLookup')
@patch('services.database_service.DatabaseService.getPortfolioValueHistory')
@patch('services.database_service.DatabaseService.getCryptoPortfolioId')
def test_get_history(mock_portfolio_id, mock_history, mock_fx):
    mock_portfolio_id.return_value = 99
    mock_history.return_value = [
        ("2026-01-31", 40000.0),
        ("2026-02-28", 47500.0),
    ]
    mock_fx.return_value = {"2026-01-31": 0.92, "2026-02-28": 0.93}
    client = create_crypto_client()
    resp = client.get('/api/crypto/history?start_date=2026-01-01&end_date=2026-12-31')
    assert resp.status_code == 200
    data = resp.json()
    assert len(data['data']) == 2


def test_get_history_invalid_dates():
    client = create_crypto_client()
    resp = client.get('/api/crypto/history?start_date=bad&end_date=2026-12-31')
    assert resp.status_code == 400
