import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from services.database_service import DatabaseService
from api.routers import equity as equity_router
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


def create_equity_client():
    """Create a minimal FastAPI app with equity router."""
    app = FastAPI()
    app.include_router(equity_router.router, prefix="/api/equity", tags=["equity"])
    return TestClient(app)


def create_net_worth_client():
    """Create a minimal FastAPI app with net_worth router."""
    app = FastAPI()
    app.include_router(net_worth_router.router, prefix="/api/net-worth", tags=["net-worth"])
    return TestClient(app)


SAMPLE_GRANT = {
    "id": 1,
    "name": "Initial Grant 2024",
    "symbol": "AAPL",
    "stock_name": "Apple Inc.",
    "total_shares": 100,
    "grant_date": "2024-01-15",
    "grant_price": 150.0,
    "share_price": 180.0,
    "currency": "USD",
    "fx_rate": 0.92,
    "vested_shares": 25,
    "unvested_shares": 75,
    "vested_value": 4500.0,
    "unvested_value": 13500.0,
    "total_value": 18000.0,
    "gain_loss": 750.0,
    "gain_loss_pct": 20.0,
    "vesting_events": [
        {"id": 1, "grant_id": 1, "date": "2025-01-15", "shares": 25, "taxed_shares": 10, "net_shares": 15, "vested": True},
        {"id": 2, "grant_id": 1, "date": "2026-01-15", "shares": 25, "taxed_shares": 10, "net_shares": 15, "vested": True},
        {"id": 3, "grant_id": 1, "date": "2027-01-15", "shares": 25, "taxed_shares": 10, "net_shares": 15, "vested": False},
        {"id": 4, "grant_id": 1, "date": "2028-01-15", "shares": 25, "taxed_shares": 10, "net_shares": 15, "vested": False},
    ],
}


@patch('services.database_service.DatabaseService.getEquityGrants')
def test_get_grants_empty(mock_get_grants):
    """Test getting grants when none exist."""
    mock_get_grants.return_value = []
    client = create_equity_client()
    resp = client.get('/api/equity/grants')
    assert resp.status_code == 200
    assert resp.json() == []


@patch('services.database_service.DatabaseService.addEquityGrant')
def test_create_grant(mock_add_grant):
    """Test creating a new equity grant with grant_price."""
    mock_add_grant.return_value = SAMPLE_GRANT
    client = create_equity_client()
    resp = client.post('/api/equity/grants', json={
        "name": "Initial Grant 2024",
        "symbol": "AAPL",
        "total_shares": 100,
        "grant_date": "2024-01-15",
        "grant_price": 150.0,
        "vesting_events": [
            {"date": "2025-01-15", "shares": 25},
            {"date": "2026-01-15", "shares": 25},
            {"date": "2027-01-15", "shares": 25},
            {"date": "2028-01-15", "shares": 25},
        ],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data['id'] == 1
    assert data['grant_price'] == 150.0
    assert data['share_price'] == 180.0
    assert data['gain_loss'] == 750.0
    assert data['gain_loss_pct'] == 20.0
    assert data['total_value'] == 18000.0
    assert len(data['vesting_events']) == 4


@patch('services.database_service.DatabaseService.addEquityGrant')
def test_create_grant_invalid_vesting_total(mock_add_grant):
    """Test that creating a grant with vesting events exceeding total_shares returns 400."""
    mock_add_grant.side_effect = ValueError("Vesting events total (200) exceeds total_shares (100)")
    client = create_equity_client()
    resp = client.post('/api/equity/grants', json={
        "name": "Bad Grant",
        "symbol": "AAPL",
        "total_shares": 100,
        "grant_date": "2024-01-15",
        "grant_price": 150.0,
        "vesting_events": [{"date": "2025-01-15", "shares": 200}],
    })
    assert resp.status_code == 400
    assert 'exceeds total_shares' in resp.json()['detail']


def test_create_grant_missing_fields():
    """Test that missing required fields are rejected."""
    client = create_equity_client()
    resp = client.post('/api/equity/grants', json={"name": "Test"})
    assert resp.status_code == 422


@patch('services.database_service.DatabaseService.getEquityGrant')
def test_get_grant(mock_get_grant):
    """Test getting a single grant."""
    mock_get_grant.return_value = SAMPLE_GRANT
    client = create_equity_client()
    resp = client.get('/api/equity/grants/1')
    assert resp.status_code == 200
    data = resp.json()
    assert data['id'] == 1
    assert data['share_price'] == 180.0
    assert data['grant_price'] == 150.0
    assert data['gain_loss'] == 750.0


@patch('services.database_service.DatabaseService.getEquityGrant')
def test_get_grant_not_found(mock_get_grant):
    """Test getting a non-existent grant returns 404."""
    mock_get_grant.side_effect = KeyError("Grant with id 999 not found")
    client = create_equity_client()
    resp = client.get('/api/equity/grants/999')
    assert resp.status_code == 404


@patch('services.database_service.DatabaseService.updateEquityGrant')
def test_update_grant(mock_update_grant):
    """Test updating a grant name."""
    updated = {**SAMPLE_GRANT, "name": "Renamed Grant"}
    mock_update_grant.return_value = updated
    client = create_equity_client()
    resp = client.put('/api/equity/grants/1', json={"name": "Renamed Grant"})
    assert resp.status_code == 200
    assert resp.json()['name'] == 'Renamed Grant'


@patch('services.database_service.DatabaseService.updateEquityGrant')
def test_update_grant_not_found(mock_update_grant):
    """Test updating a non-existent grant returns 404."""
    mock_update_grant.side_effect = KeyError("Grant with id 999 not found")
    client = create_equity_client()
    resp = client.put('/api/equity/grants/999', json={"name": "Test"})
    assert resp.status_code == 404


@patch('services.database_service.DatabaseService.deleteEquityGrant')
def test_delete_grant(mock_delete_grant):
    """Test deleting a grant."""
    mock_delete_grant.return_value = None
    client = create_equity_client()
    resp = client.delete('/api/equity/grants/1')
    assert resp.status_code == 204
    mock_delete_grant.assert_called_once_with(1)


@patch('services.database_service.DatabaseService.deleteEquityGrant')
def test_delete_grant_not_found(mock_delete_grant):
    """Test deleting a non-existent grant returns 404."""
    mock_delete_grant.side_effect = KeyError("Grant with id 999 not found")
    client = create_equity_client()
    resp = client.delete('/api/equity/grants/999')
    assert resp.status_code == 404


@patch('services.database_service.DatabaseService.addEquityVestingEvent')
def test_add_vesting_event(mock_add_event):
    """Test adding a vesting event."""
    mock_add_event.return_value = {
        "id": 5, "grant_id": 1, "date": "2029-01-15", "shares": 10, "taxed_shares": 4, "net_shares": 6, "vested": False,
    }
    client = create_equity_client()
    resp = client.post('/api/equity/grants/1/vesting-events', json={
        "date": "2029-01-15", "shares": 10, "taxed_shares": 4,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data['id'] == 5
    assert data['shares'] == 10
    assert data['taxed_shares'] == 4
    assert data['net_shares'] == 6


@patch('services.database_service.DatabaseService.addEquityVestingEvent')
def test_add_vesting_event_exceeds_total(mock_add_event):
    """Test that adding a vesting event exceeding total_shares returns 400."""
    mock_add_event.side_effect = ValueError("Adding 50 shares would exceed total_shares (100)")
    client = create_equity_client()
    resp = client.post('/api/equity/grants/1/vesting-events', json={
        "date": "2029-01-15", "shares": 50,
    })
    assert resp.status_code == 400
    assert 'exceed' in resp.json()['detail']


@patch('services.database_service.DatabaseService.updateEquityVestingEvent')
def test_update_vesting_event(mock_update_event):
    """Test updating a vesting event."""
    mock_update_event.return_value = {
        "id": 1, "grant_id": 1, "date": "2025-01-15", "shares": 25, "taxed_shares": 12, "net_shares": 13, "vested": True,
    }
    client = create_equity_client()
    resp = client.put('/api/equity/grants/1/vesting-events/1', json={
        "taxed_shares": 12,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data['taxed_shares'] == 12
    assert data['net_shares'] == 13


@patch('services.database_service.DatabaseService.updateEquityVestingEvent')
def test_update_vesting_event_not_found(mock_update_event):
    """Test updating a non-existent vesting event returns 404."""
    mock_update_event.side_effect = KeyError("Vesting event with id 999 not found")
    client = create_equity_client()
    resp = client.put('/api/equity/grants/1/vesting-events/999', json={"shares": 10})
    assert resp.status_code == 404


@patch('services.database_service.DatabaseService.updateEquityVestingEvent')
def test_update_vesting_event_exceeds_total(mock_update_event):
    """Test updating a vesting event that would exceed total_shares returns 400."""
    mock_update_event.side_effect = ValueError("Updating to 200 shares would exceed total_shares (100)")
    client = create_equity_client()
    resp = client.put('/api/equity/grants/1/vesting-events/1', json={"shares": 200})
    assert resp.status_code == 400
    assert 'exceed' in resp.json()['detail']


@patch('services.database_service.DatabaseService.deleteEquityVestingEvent')
def test_delete_vesting_event(mock_delete_event):
    """Test deleting a vesting event."""
    mock_delete_event.return_value = None
    client = create_equity_client()
    resp = client.delete('/api/equity/grants/1/vesting-events/5')
    assert resp.status_code == 204
    mock_delete_event.assert_called_once_with(5)


@patch('services.database_service.DatabaseService.deleteEquityVestingEvent')
def test_delete_vesting_event_not_found(mock_delete_event):
    """Test deleting a non-existent vesting event returns 404."""
    mock_delete_event.side_effect = KeyError("Vesting event with id 999 not found")
    client = create_equity_client()
    resp = client.delete('/api/equity/grants/1/vesting-events/999')
    assert resp.status_code == 404


@patch('services.database_service.DatabaseService.getEquitySummary')
def test_get_summary(mock_summary):
    """Test getting equity summary."""
    mock_summary.return_value = {
        "total_vested_value": 4500.0,
        "total_unvested_value": 13500.0,
        "total_gain_loss": 750.0,
        "total_gain_loss_pct": 20.0,
        "grants_count": 1,
        "currency": "USD",
    }
    client = create_equity_client()
    resp = client.get('/api/equity/summary')
    assert resp.status_code == 200
    data = resp.json()
    assert data['total_vested_value'] == 4500.0
    assert data['total_unvested_value'] == 13500.0
    assert data['total_gain_loss'] == 750.0
    assert data['total_gain_loss_pct'] == 20.0
    assert data['grants_count'] == 1
    assert data['currency'] == 'USD'


@patch('services.database_service.DatabaseService.getEquitySummary')
def test_get_summary_empty(mock_summary):
    """Test equity summary with no grants."""
    mock_summary.return_value = {
        "total_vested_value": 0.0,
        "total_unvested_value": 0.0,
        "total_gain_loss": 0.0,
        "total_gain_loss_pct": 0.0,
        "grants_count": 0,
        "currency": "USD",
    }
    client = create_equity_client()
    resp = client.get('/api/equity/summary')
    assert resp.status_code == 200
    data = resp.json()
    assert data['grants_count'] == 0
    assert data['total_vested_value'] == 0.0


@patch('services.database_service.DatabaseService.getEquityValueHistory')
def test_get_history(mock_history):
    """Test getting equity value history."""
    mock_history.return_value = [
        ("2024-01-31", 3000.0),
        ("2024-02-28", 3200.0),
    ]
    client = create_equity_client()
    resp = client.get('/api/equity/history?start_date=2024-01-01&end_date=2024-12-31')
    assert resp.status_code == 200
    data = resp.json()
    assert len(data['data']) == 2
    assert data['data'][0]['date'] == '2024-01-31'
    assert data['data'][0]['value'] == 3000.0
    assert data['data'][1]['date'] == '2024-02-28'
    assert data['data'][1]['value'] == 3200.0


def test_get_history_invalid_dates():
    """Test equity history with invalid dates."""
    client = create_equity_client()

    resp = client.get('/api/equity/history?start_date=bad&end_date=2024-12-31')
    assert resp.status_code == 400
    assert 'Invalid date format' in resp.json()['detail']

    resp = client.get('/api/equity/history?start_date=2024-12-31&end_date=2024-01-01')
    assert resp.status_code == 400
    assert 'start_date must be before' in resp.json()['detail']


@patch('services.database_service.DatabaseService.getEquityVestedTotal')
@patch('services.database_service.DatabaseService.getNetWorthAssets')
@patch('services.portfolio_service.PortfolioService.calculatePortfolioValue')
def test_net_worth_includes_vested_equity(mock_pea_value, mock_get_assets, mock_vested_total):
    """Test that GET /net-worth/current includes equity when equity exists."""
    mock_pea_value.return_value = 50000.0
    mock_get_assets.return_value = []
    mock_vested_total.return_value = 4140.0

    client = create_net_worth_client()
    resp = client.get('/api/net-worth/current')

    assert resp.status_code == 200
    data = resp.json()
    assert data['total'] == 54140.0
    assert len(data['assets']) == 2
    assert data['assets'][0]['id'] == 'pea'
    assert data['assets'][1]['id'] == 'equity'
    assert data['assets'][1]['value'] == 4140.0
