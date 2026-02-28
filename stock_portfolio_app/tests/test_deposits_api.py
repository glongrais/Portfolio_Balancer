import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from services.database_service import DatabaseService
from api.routers import deposits as deposits_router


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
    """Create a minimal FastAPI app with deposits router."""
    app = FastAPI()
    app.include_router(deposits_router.router, prefix="/api/portfolio", tags=["deposits"])
    return TestClient(app)


@patch('services.database_service.DatabaseService.getDeposits')
def test_get_deposits(mock_get_deposits):
    """Test getting all deposits."""
    mock_get_deposits.return_value = [
        {"depositid": 1, "datestamp": "2024-01-15", "amount": 1000.0, "portfolioid": 1, "currency": "EUR"},
        {"depositid": 2, "datestamp": "2024-02-15", "amount": 500.0, "portfolioid": 1, "currency": "EUR"},
    ]

    client = create_test_client()
    resp = client.get('/api/portfolio/1/deposits/')

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]['depositid'] == 1
    assert data[0]['amount'] == 1000.0
    assert data[0]['currency'] == 'EUR'
    assert data[1]['depositid'] == 2
    assert data[1]['amount'] == 500.0
    mock_get_deposits.assert_called_once_with(100, portfolio_id=1)


@patch('services.database_service.DatabaseService.getDeposits')
def test_get_deposits_with_limit(mock_get_deposits):
    """Test getting deposits with a custom limit."""
    mock_get_deposits.return_value = [
        {"depositid": 1, "datestamp": "2024-01-15", "amount": 1000.0, "portfolioid": 1, "currency": "EUR"},
    ]

    client = create_test_client()
    resp = client.get('/api/portfolio/1/deposits/?limit=5')

    assert resp.status_code == 200
    mock_get_deposits.assert_called_once_with(5, portfolio_id=1)


@patch('services.database_service.DatabaseService.getDeposits')
def test_get_deposits_empty(mock_get_deposits):
    """Test getting deposits when none exist."""
    mock_get_deposits.return_value = []

    client = create_test_client()
    resp = client.get('/api/portfolio/1/deposits/')

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 0


@patch('services.database_service.DatabaseService.getDeposits')
def test_get_deposits_error(mock_get_deposits):
    """Test error handling when fetching deposits fails."""
    mock_get_deposits.side_effect = Exception("Database error")

    client = create_test_client()
    resp = client.get('/api/portfolio/1/deposits/')

    assert resp.status_code == 500
    assert 'Failed to fetch deposits' in resp.json()['detail']


def test_get_deposits_invalid_limit():
    """Test that invalid limit values are rejected."""
    client = create_test_client()

    resp = client.get('/api/portfolio/1/deposits/?limit=0')
    assert resp.status_code == 422

    resp = client.get('/api/portfolio/1/deposits/?limit=1001')
    assert resp.status_code == 422


@patch('services.database_service.DatabaseService.getTotalDeposits')
def test_get_total_deposits(mock_get_total):
    """Test getting total deposits."""
    mock_get_total.return_value = 5000.0

    client = create_test_client()
    resp = client.get('/api/portfolio/1/deposits/total')

    assert resp.status_code == 200
    data = resp.json()
    assert data['total_deposits'] == 5000.0
    assert data['currency'] == 'EUR'


@patch('services.database_service.DatabaseService.getTotalDeposits')
def test_get_total_deposits_zero(mock_get_total):
    """Test getting total deposits when none exist."""
    mock_get_total.return_value = 0.0

    client = create_test_client()
    resp = client.get('/api/portfolio/1/deposits/total')

    assert resp.status_code == 200
    data = resp.json()
    assert data['total_deposits'] == 0.0


@patch('services.database_service.DatabaseService.getTotalDeposits')
def test_get_total_deposits_error(mock_get_total):
    """Test error handling when fetching total deposits fails."""
    mock_get_total.side_effect = Exception("Database error")

    client = create_test_client()
    resp = client.get('/api/portfolio/1/deposits/total')

    assert resp.status_code == 500
    assert 'Failed to fetch total deposits' in resp.json()['detail']


@patch('services.database_service.DatabaseService.addDeposit')
def test_add_deposit(mock_add_deposit):
    """Test adding a new deposit."""
    mock_add_deposit.return_value = {
        "depositid": 1,
        "datestamp": "2024-03-15",
        "amount": 2000.0,
        "portfolioid": 1,
        "currency": "EUR",
    }

    client = create_test_client()
    resp = client.post('/api/portfolio/1/deposits/', json={
        "datestamp": "2024-03-15T00:00:00",
        "amount": 2000.0,
    })

    assert resp.status_code == 201
    data = resp.json()
    assert data['depositid'] == 1
    assert data['datestamp'] == '2024-03-15'
    assert data['amount'] == 2000.0
    assert data['portfolioid'] == 1
    assert data['currency'] == 'EUR'
    mock_add_deposit.assert_called_once_with("2024-03-15", 2000.0, portfolio_id=1)


@patch('services.database_service.DatabaseService.addDeposit')
def test_add_deposit_error(mock_add_deposit):
    """Test error handling when adding a deposit fails."""
    mock_add_deposit.side_effect = Exception("Database error")

    client = create_test_client()
    resp = client.post('/api/portfolio/1/deposits/', json={
        "datestamp": "2024-03-15T00:00:00",
        "amount": 2000.0,
    })

    assert resp.status_code == 500
    assert 'Failed to add deposit' in resp.json()['detail']


def test_add_deposit_missing_fields():
    """Test that missing required fields are rejected."""
    client = create_test_client()

    resp = client.post('/api/portfolio/1/deposits/', json={"datestamp": "2024-03-15T00:00:00"})
    assert resp.status_code == 422

    resp = client.post('/api/portfolio/1/deposits/', json={"amount": 2000.0})
    assert resp.status_code == 422


def test_add_deposit_invalid_amount():
    """Test that non-positive amounts are rejected."""
    client = create_test_client()

    resp = client.post('/api/portfolio/1/deposits/', json={
        "datestamp": "2024-03-15T00:00:00",
        "amount": 0,
    })
    assert resp.status_code == 422

    resp = client.post('/api/portfolio/1/deposits/', json={
        "datestamp": "2024-03-15T00:00:00",
        "amount": -100.0,
    })
    assert resp.status_code == 422
