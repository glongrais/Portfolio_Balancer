import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch

from services.database_service import DatabaseService
from api.routers import savings as savings_router
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


def create_savings_client():
    app = FastAPI()
    app.include_router(savings_router.router, prefix="/api/savings", tags=["savings"])
    return TestClient(app)


def create_net_worth_client():
    app = FastAPI()
    app.include_router(net_worth_router.router, prefix="/api/net-worth", tags=["net-worth"])
    return TestClient(app)


SAMPLE_ACCOUNT = {
    "id": 1,
    "name": "Livret A",
    "bank": "BoursoBank",
    "currency": "EUR",
    "balance": 1000.0,
    "interest_rate": 3.0,
    "created_at": "2026-03-04",
    "updated_at": "2026-03-04",
}

SAMPLE_TXN = {
    "id": 1,
    "account_id": 1,
    "type": "DEPOSIT",
    "amount": 500.0,
    "datestamp": "2026-03-04",
    "note": "",
}


# ── Account CRUD tests ─────────────────────────────────────────

@patch('services.database_service.DatabaseService.getSavingsAccounts')
def test_get_accounts_empty(mock_get):
    mock_get.return_value = []
    client = create_savings_client()
    resp = client.get('/api/savings/accounts')
    assert resp.status_code == 200
    assert resp.json() == []


@patch('services.database_service.DatabaseService.addSavingsAccount')
def test_create_account(mock_add):
    mock_add.return_value = SAMPLE_ACCOUNT
    client = create_savings_client()
    resp = client.post('/api/savings/accounts', json={
        "name": "Livret A",
        "bank": "BoursoBank",
        "currency": "EUR",
        "balance": 1000.0,
        "interest_rate": 3.0,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data['id'] == 1
    assert data['name'] == 'Livret A'
    assert data['balance'] == 1000.0


@patch('services.database_service.DatabaseService.getSavingsAccount')
def test_get_account(mock_get):
    mock_get.return_value = SAMPLE_ACCOUNT
    client = create_savings_client()
    resp = client.get('/api/savings/accounts/1')
    assert resp.status_code == 200
    assert resp.json()['id'] == 1


@patch('services.database_service.DatabaseService.getSavingsAccount')
def test_get_account_not_found(mock_get):
    mock_get.side_effect = KeyError("Savings account with id 999 not found")
    client = create_savings_client()
    resp = client.get('/api/savings/accounts/999')
    assert resp.status_code == 404


@patch('services.database_service.DatabaseService.updateSavingsAccount')
def test_update_account(mock_update):
    updated = {**SAMPLE_ACCOUNT, "name": "Livret A+", "interest_rate": 3.5}
    mock_update.return_value = updated
    client = create_savings_client()
    resp = client.put('/api/savings/accounts/1', json={"name": "Livret A+", "interest_rate": 3.5})
    assert resp.status_code == 200
    assert resp.json()['name'] == 'Livret A+'
    assert resp.json()['interest_rate'] == 3.5


@patch('services.database_service.DatabaseService.updateSavingsAccount')
def test_update_account_not_found(mock_update):
    mock_update.side_effect = KeyError("Savings account with id 999 not found")
    client = create_savings_client()
    resp = client.put('/api/savings/accounts/999', json={"name": "Test"})
    assert resp.status_code == 404


@patch('services.database_service.DatabaseService.deleteSavingsAccount')
def test_delete_account(mock_delete):
    mock_delete.return_value = None
    client = create_savings_client()
    resp = client.delete('/api/savings/accounts/1')
    assert resp.status_code == 204
    mock_delete.assert_called_once_with(1)


@patch('services.database_service.DatabaseService.deleteSavingsAccount')
def test_delete_account_not_found(mock_delete):
    mock_delete.side_effect = KeyError("Savings account with id 999 not found")
    client = create_savings_client()
    resp = client.delete('/api/savings/accounts/999')
    assert resp.status_code == 404


# ── Transaction tests ───────────────────────────────────────────

@patch('services.database_service.DatabaseService.getSavingsTransactions')
def test_get_transactions(mock_get):
    mock_get.return_value = [SAMPLE_TXN]
    client = create_savings_client()
    resp = client.get('/api/savings/accounts/1/transactions')
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]['type'] == 'DEPOSIT'


@patch('services.database_service.DatabaseService.getSavingsTransactions')
def test_get_transactions_not_found(mock_get):
    mock_get.side_effect = KeyError("Savings account with id 999 not found")
    client = create_savings_client()
    resp = client.get('/api/savings/accounts/999/transactions')
    assert resp.status_code == 404


@patch('services.database_service.DatabaseService.addSavingsTransaction')
def test_add_transaction(mock_add):
    mock_add.return_value = SAMPLE_TXN
    client = create_savings_client()
    resp = client.post('/api/savings/accounts/1/transactions', json={
        "type": "DEPOSIT",
        "amount": 500.0,
        "datestamp": "2026-03-04",
    })
    assert resp.status_code == 201
    assert resp.json()['amount'] == 500.0


@patch('services.database_service.DatabaseService.addSavingsTransaction')
def test_add_withdrawal_exceeds_balance(mock_add):
    mock_add.side_effect = ValueError("Cannot withdraw 5000: only 1000.0 available")
    client = create_savings_client()
    resp = client.post('/api/savings/accounts/1/transactions', json={
        "type": "WITHDRAWAL",
        "amount": 5000.0,
        "datestamp": "2026-03-04",
    })
    assert resp.status_code == 400
    assert 'Cannot withdraw' in resp.json()['detail']


@patch('services.database_service.DatabaseService.updateSavingsTransaction')
def test_update_transaction(mock_update):
    updated = {**SAMPLE_TXN, "amount": 750.0}
    mock_update.return_value = updated
    client = create_savings_client()
    resp = client.put('/api/savings/accounts/1/transactions/1', json={"amount": 750.0})
    assert resp.status_code == 200
    assert resp.json()['amount'] == 750.0


@patch('services.database_service.DatabaseService.updateSavingsTransaction')
def test_update_transaction_not_found(mock_update):
    mock_update.side_effect = KeyError("Savings transaction with id 999 not found")
    client = create_savings_client()
    resp = client.put('/api/savings/accounts/1/transactions/999', json={"amount": 100.0})
    assert resp.status_code == 404


@patch('services.database_service.DatabaseService.deleteSavingsTransaction')
def test_delete_transaction(mock_delete):
    mock_delete.return_value = None
    client = create_savings_client()
    resp = client.delete('/api/savings/accounts/1/transactions/1')
    assert resp.status_code == 204
    mock_delete.assert_called_once_with(1)


@patch('services.database_service.DatabaseService.deleteSavingsTransaction')
def test_delete_transaction_not_found(mock_delete):
    mock_delete.side_effect = KeyError("Savings transaction with id 999 not found")
    client = create_savings_client()
    resp = client.delete('/api/savings/accounts/1/transactions/999')
    assert resp.status_code == 404


# ── Summary and history tests ───────────────────────────────────

@patch('services.database_service.DatabaseService.getSavingsAccountsTotal')
@patch('services.database_service.DatabaseService.getSavingsAccounts')
def test_get_summary(mock_accounts, mock_total):
    mock_accounts.return_value = [SAMPLE_ACCOUNT]
    mock_total.return_value = 1000.0
    client = create_savings_client()
    resp = client.get('/api/savings/summary')
    assert resp.status_code == 200
    data = resp.json()
    assert data['total_balance'] == 1000.0
    assert data['accounts_count'] == 1
    assert len(data['accounts']) == 1


@patch('services.database_service.DatabaseService.getSavingsBalanceHistory')
def test_get_history(mock_history):
    mock_history.return_value = [("2026-01-31", 800.0), ("2026-02-28", 1000.0)]
    client = create_savings_client()
    resp = client.get('/api/savings/history?start_date=2026-01-01&end_date=2026-12-31')
    assert resp.status_code == 200
    data = resp.json()
    assert len(data['data']) == 2
    assert data['data'][0]['date'] == '2026-01-31'
    assert data['data'][0]['balance'] == 800.0


def test_get_history_invalid_dates():
    client = create_savings_client()
    resp = client.get('/api/savings/history?start_date=bad&end_date=2026-12-31')
    assert resp.status_code == 400

    resp = client.get('/api/savings/history?start_date=2026-12-31&end_date=2026-01-01')
    assert resp.status_code == 400


# ── Net worth integration ───────────────────────────────────────

@patch('services.database_service.DatabaseService.getSavingsAccountsTotal')
@patch('services.database_service.DatabaseService.getEquityVestedTotal')
@patch('services.database_service.DatabaseService.getNetWorthAssets')
@patch('services.portfolio_service.PortfolioService.calculatePortfolioValue')
@patch('services.database_service.DatabaseService.getPortfolios')
def test_net_worth_includes_savings(mock_portfolios, mock_pea_value, mock_assets, mock_equity, mock_savings):
    mock_portfolios.return_value = [{"portfolio_id": 1, "name": "PEA", "currency": "EUR"}]
    mock_pea_value.return_value = 50000.0
    mock_assets.return_value = []
    mock_equity.return_value = 0.0
    mock_savings.return_value = 5000.0

    client = create_net_worth_client()
    resp = client.get('/api/net-worth/current')
    assert resp.status_code == 200
    data = resp.json()
    assert data['total'] == 55000.0
    asset_ids = [a['id'] for a in data['assets']]
    assert 'savings' in asset_ids
    savings_asset = next(a for a in data['assets'] if a['id'] == 'savings')
    assert savings_asset['value'] == 5000.0
