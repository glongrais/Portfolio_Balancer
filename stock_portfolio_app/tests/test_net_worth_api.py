import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from services.database_service import DatabaseService
from api.routers import net_worth as net_worth_router


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
    """Create a minimal FastAPI app with net_worth router."""
    app = FastAPI()
    app.include_router(net_worth_router.router, prefix="/api/net-worth", tags=["net-worth"])
    return TestClient(app)


SAMPLE_PORTFOLIOS = [
    {"portfolio_id": 1, "name": "PEA", "currency": "EUR"},
    {"portfolio_id": 2, "name": "ISK", "currency": "SEK"},
]


@patch('services.database_service.DatabaseService.getEquityVestedTotal')
@patch('services.stock_api.StockAPI.get_fx_rate')
@patch('services.portfolio_service.PortfolioService.calculatePortfolioValue')
@patch('services.database_service.DatabaseService.getNetWorthAssets')
@patch('services.database_service.DatabaseService.getPortfolios')
def test_get_current_net_worth(mock_get_portfolios, mock_get_assets, mock_portfolio_value, mock_fx_rate, mock_equity_total):
    """Test getting current net worth with multiple portfolios + stored assets."""
    mock_get_portfolios.return_value = SAMPLE_PORTFOLIOS
    mock_portfolio_value.side_effect = lambda pid: {1: 89000.0, 2: 50000.0}[pid]
    mock_fx_rate.return_value = 0.09  # SEK to EUR
    mock_equity_total.return_value = 0.0
    mock_get_assets.return_value = [
        {"id": "savings", "label": "Savings", "current_value": 10000.0, "updated_at": "2026-02-26"},
    ]

    client = create_test_client()
    resp = client.get('/api/net-worth/current')

    assert resp.status_code == 200
    data = resp.json()
    # PEA: 89000, ISK: 50000 * 0.09 = 4500, Savings: 10000
    assert len(data['assets']) == 3
    assert data['assets'][0]['id'] == 'pea'
    assert data['assets'][0]['value'] == 89000.0
    assert data['assets'][1]['id'] == 'isk'
    assert data['assets'][1]['value'] == 4500.0
    assert data['assets'][2]['id'] == 'savings'
    assert data['assets'][2]['value'] == 10000.0
    assert data['total'] == 103500.0
    assert 'last_updated' in data
    mock_fx_rate.assert_called_once_with("SEK", "EUR")


@patch('services.database_service.DatabaseService.getEquityVestedTotal')
@patch('services.portfolio_service.PortfolioService.calculatePortfolioValue')
@patch('services.database_service.DatabaseService.getNetWorthAssets')
@patch('services.database_service.DatabaseService.getPortfolios')
def test_get_current_net_worth_no_assets(mock_get_portfolios, mock_get_assets, mock_portfolio_value, mock_equity_total):
    """Test getting current net worth with only portfolios (no stored assets)."""
    mock_get_portfolios.return_value = [{"portfolio_id": 1, "name": "PEA", "currency": "EUR"}]
    mock_portfolio_value.return_value = 50000.0
    mock_equity_total.return_value = 0.0
    mock_get_assets.return_value = []

    client = create_test_client()
    resp = client.get('/api/net-worth/current')

    assert resp.status_code == 200
    data = resp.json()
    assert data['total'] == 50000.0
    assert len(data['assets']) == 1
    assert data['assets'][0]['id'] == 'pea'
    assert data['assets'][0]['value'] == 50000.0


@patch('services.database_service.DatabaseService.getPortfolios')
def test_get_current_net_worth_error(mock_get_portfolios):
    """Test error handling when fetching current net worth fails."""
    mock_get_portfolios.side_effect = Exception("Database error")

    client = create_test_client()
    resp = client.get('/api/net-worth/current')

    assert resp.status_code == 500
    assert 'Failed to fetch current net worth' in resp.json()['detail']


@patch('services.database_service.DatabaseService.getNetWorthSnapshots')
@patch('services.database_service.DatabaseService.getEquityValueHistory')
@patch('services.database_service.DatabaseService.getPortfolioValueHistory')
@patch('services.database_service.DatabaseService.getPortfolios')
def test_get_history(mock_get_portfolios, mock_portfolio_history, mock_equity_history, mock_snapshots):
    """Test getting net worth history with multiple portfolios + stored asset snapshots."""
    mock_get_portfolios.return_value = [{"portfolio_id": 1, "name": "PEA", "currency": "EUR"}]
    mock_portfolio_history.return_value = [
        ("2024-01-31", 60000.0),
        ("2024-02-28", 62000.0),
    ]
    mock_equity_history.return_value = []
    mock_snapshots.return_value = [
        {"date": "2024-01-31", "asset_id": "savings", "value": 15000.0},
        {"date": "2024-02-28", "asset_id": "savings", "value": 15500.0},
    ]

    client = create_test_client()
    resp = client.get('/api/net-worth/history?start_date=2024-01-01&end_date=2024-12-31')

    assert resp.status_code == 200
    data = resp.json()
    assert len(data['data']) == 2
    assert data['data'][0]['date'] == '2024-01-31'
    assert data['data'][0]['total'] == 75000.0
    assert data['data'][0]['assets']['pea'] == 60000.0
    assert data['data'][0]['assets']['savings'] == 15000.0
    assert data['data'][1]['date'] == '2024-02-28'
    assert data['data'][1]['total'] == 77500.0


@patch('services.database_service.DatabaseService.getNetWorthSnapshots')
@patch('services.database_service.DatabaseService.getEquityValueHistory')
@patch('services.database_service.DatabaseService.getPortfolioValueHistory')
@patch('services.database_service.DatabaseService.getPortfolios')
def test_get_history_includes_equity(mock_get_portfolios, mock_portfolio_history, mock_equity_history, mock_snapshots):
    """Test that net worth history includes equity from equity grants."""
    mock_get_portfolios.return_value = [{"portfolio_id": 1, "name": "PEA", "currency": "EUR"}]
    mock_portfolio_history.return_value = [
        ("2024-01-31", 50000.0),
        ("2024-02-28", 52000.0),
    ]
    mock_equity_history.return_value = [
        ("2024-01-31", 4000.0),
        ("2024-02-28", 4200.0),
    ]
    mock_snapshots.return_value = []

    client = create_test_client()
    resp = client.get('/api/net-worth/history?start_date=2024-01-01&end_date=2024-12-31')

    assert resp.status_code == 200
    data = resp.json()
    assert len(data['data']) == 2
    assert data['data'][0]['date'] == '2024-01-31'
    assert data['data'][0]['total'] == 54000.0
    assert data['data'][0]['assets']['pea'] == 50000.0
    assert data['data'][0]['assets']['equity'] == 4000.0
    assert data['data'][1]['date'] == '2024-02-28'
    assert data['data'][1]['total'] == 56200.0
    assert data['data'][1]['assets']['equity'] == 4200.0


def test_get_history_invalid_dates():
    """Test that invalid date formats are rejected."""
    client = create_test_client()

    resp = client.get('/api/net-worth/history?start_date=bad&end_date=2024-12-31')
    assert resp.status_code == 400
    assert 'Invalid date format' in resp.json()['detail']

    resp = client.get('/api/net-worth/history?start_date=2024-12-31&end_date=2024-01-01')
    assert resp.status_code == 400
    assert 'start_date must be before' in resp.json()['detail']


@patch('services.database_service.DatabaseService.addNetWorthAsset')
def test_create_asset(mock_add):
    """Test creating a new asset category."""
    mock_add.return_value = {
        "id": "cto",
        "label": "CTO",
        "current_value": 12000.0,
        "updated_at": "2026-02-26",
    }

    client = create_test_client()
    resp = client.post('/api/net-worth/assets', json={
        "id": "cto",
        "label": "CTO",
        "current_value": 12000.0,
    })

    assert resp.status_code == 201
    data = resp.json()
    assert data['id'] == 'cto'
    assert data['label'] == 'CTO'
    assert data['current_value'] == 12000.0
    assert data['updated_at'] == '2026-02-26'
    mock_add.assert_called_once_with("cto", "CTO", 12000.0)


@patch('services.database_service.DatabaseService.addNetWorthAsset')
def test_create_asset_duplicate(mock_add):
    """Test that creating a duplicate asset returns 409."""
    mock_add.side_effect = ValueError("Asset with id 'cto' already exists")

    client = create_test_client()
    resp = client.post('/api/net-worth/assets', json={
        "id": "cto",
        "label": "CTO",
        "current_value": 12000.0,
    })

    assert resp.status_code == 409
    assert 'already exists' in resp.json()['detail']


def test_create_asset_missing_fields():
    """Test that missing required fields are rejected."""
    client = create_test_client()

    resp = client.post('/api/net-worth/assets', json={"id": "cto"})
    assert resp.status_code == 422

    resp = client.post('/api/net-worth/assets', json={"label": "CTO", "current_value": 100.0})
    assert resp.status_code == 422


@patch('services.database_service.DatabaseService.updateNetWorthAsset')
def test_update_asset(mock_update):
    """Test updating an existing asset."""
    mock_update.return_value = {
        "id": "cto",
        "label": "CTO",
        "current_value": 15000.0,
        "updated_at": "2026-02-26",
    }

    client = create_test_client()
    resp = client.put('/api/net-worth/assets/cto', json={"current_value": 15000.0})

    assert resp.status_code == 200
    data = resp.json()
    assert data['current_value'] == 15000.0
    mock_update.assert_called_once_with("cto", None, 15000.0)


@patch('services.database_service.DatabaseService.updateNetWorthAsset')
def test_update_asset_not_found(mock_update):
    """Test that updating a non-existent asset returns 404."""
    mock_update.side_effect = KeyError("Asset with id 'unknown' not found")

    client = create_test_client()
    resp = client.put('/api/net-worth/assets/unknown', json={"current_value": 100.0})

    assert resp.status_code == 404


@patch('services.database_service.DatabaseService.deleteNetWorthAsset')
def test_delete_asset(mock_delete):
    """Test deleting an asset."""
    mock_delete.return_value = None

    client = create_test_client()
    resp = client.delete('/api/net-worth/assets/cto')

    assert resp.status_code == 204
    mock_delete.assert_called_once_with("cto")


@patch('services.database_service.DatabaseService.deleteNetWorthAsset')
def test_delete_asset_not_found(mock_delete):
    """Test that deleting a non-existent asset returns 404."""
    mock_delete.side_effect = KeyError("Asset with id 'unknown' not found")

    client = create_test_client()
    resp = client.delete('/api/net-worth/assets/unknown')

    assert resp.status_code == 404
