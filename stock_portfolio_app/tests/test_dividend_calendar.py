"""
Tests for dividend calendar feature:
- Projection algorithm (_projectDividends)
- Calendar data method (getDividendCalendar)
- API endpoint (GET /portfolio/dividends/calendar)
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.database_service import DatabaseService
from models.Stock import Stock
from models.Position import Position
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
    app = FastAPI()
    app.include_router(portfolio_router.router, prefix="/api/portfolio", tags=["portfolio"])
    return TestClient(app)


# ── _projectDividends tests ──────────────────────────────────────────

@patch('sqlite3.connect')
def test_projectDividends_quarterly(mock_connect):
    """Quarterly dividends (~91 days apart) should project the next quarter."""
    mock_conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value.fetchall.return_value = [
        ("2024-01-15", 0.50),
        ("2024-04-15", 0.50),
        ("2024-07-15", 0.52),
        ("2024-10-15", 0.52),
    ]

    result = DatabaseService._projectDividends(1, "2025-01-01", "2025-12-31")

    assert len(result) > 0
    for item in result:
        assert item["amount_per_share"] == 0.52
        assert item["date"] >= "2025-01-01"
        assert item["date"] <= "2025-12-31"


@patch('sqlite3.connect')
def test_projectDividends_semiannual(mock_connect):
    """Semi-annual dividends (~182 days apart) should project correctly."""
    mock_conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value.fetchall.return_value = [
        ("2023-06-15", 1.00),
        ("2023-12-15", 1.00),
        ("2024-06-15", 1.10),
        ("2024-12-15", 1.10),
    ]

    result = DatabaseService._projectDividends(1, "2025-01-01", "2025-12-31")

    assert len(result) >= 1
    assert result[0]["amount_per_share"] == 1.10


@patch('sqlite3.connect')
def test_projectDividends_annual(mock_connect):
    """Annual dividends (~365 days apart) should project one year out."""
    mock_conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value.fetchall.return_value = [
        ("2022-05-10", 2.00),
        ("2023-05-10", 2.20),
        ("2024-05-10", 2.40),
    ]

    result = DatabaseService._projectDividends(1, "2025-01-01", "2025-12-31")

    assert len(result) == 1
    assert result[0]["amount_per_share"] == 2.40
    assert "2025-05" in result[0]["date"]


@patch('sqlite3.connect')
def test_projectDividends_insufficient_data(mock_connect):
    """With fewer than 2 historical records, no projection is possible."""
    mock_conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value.fetchall.return_value = [
        ("2024-06-15", 0.50),
    ]

    result = DatabaseService._projectDividends(1, "2025-01-01", "2025-12-31")

    assert result == []


@patch('sqlite3.connect')
def test_projectDividends_no_data(mock_connect):
    """With no historical records, return empty."""
    mock_conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value.fetchall.return_value = []

    result = DatabaseService._projectDividends(1, "2025-01-01", "2025-12-31")

    assert result == []


@patch('sqlite3.connect')
def test_projectDividends_caps_at_12_months(mock_connect):
    """Projections should not go beyond 12 months from the last known date."""
    mock_conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value.fetchall.return_value = [
        ("2024-01-15", 0.50),
        ("2024-04-15", 0.50),
        ("2024-07-15", 0.50),
        ("2024-10-15", 0.50),
    ]

    # Request 3 years out
    result = DatabaseService._projectDividends(1, "2025-01-01", "2027-12-31")

    # Last known date is 2024-10-15, so projections capped at 2025-10-15
    for item in result:
        assert item["date"] <= "2025-10-15"


@patch('sqlite3.connect')
def test_projectDividends_no_overlap_with_historical(mock_connect):
    """Projected dates that match historical dates should be excluded."""
    mock_conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    # Two annual dividends, and the projected date would land on 2025-05-10
    mock_conn.execute.return_value.fetchall.return_value = [
        ("2023-05-10", 2.00),
        ("2024-05-10", 2.20),
        ("2025-05-10", 2.40),  # This already exists
    ]

    result = DatabaseService._projectDividends(1, "2025-01-01", "2025-12-31")

    # The projected date 2025-05-10 should be excluded since it's historical
    projected_dates = [item["date"] for item in result]
    assert "2025-05-10" not in projected_dates


@patch('sqlite3.connect')
def test_projectDividends_only_within_range(mock_connect):
    """Projected dates before start_date should be excluded."""
    mock_conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value.fetchall.return_value = [
        ("2024-01-15", 0.50),
        ("2024-04-15", 0.50),
        ("2024-07-15", 0.50),
        ("2024-10-15", 0.50),
    ]

    result = DatabaseService._projectDividends(1, "2025-06-01", "2025-12-31")

    for item in result:
        assert item["date"] >= "2025-06-01"
        assert item["date"] <= "2025-12-31"


# ── getDividendCalendar tests ────────────────────────────────────────

@patch('sqlite3.connect')
def test_getDividendCalendar_historical_only(mock_connect):
    """Past date range should return only historical events."""
    mock_conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn

    # First call: historical query returns rows; subsequent calls: projection queries return empty
    mock_conn.execute.return_value.fetchall.side_effect = [
        # Historical dividends in range
        [("2024-03-15", 0.50, 1, "AAPL", "Apple Inc.")],
        # _projectDividends query for stockid=1 (returns empty = insufficient data)
        [],
    ]

    stock = Stock(stockid=1, symbol='AAPL', name='Apple Inc.', price=150.0)
    position = Position(stockid=1, quantity=10, stock=stock)
    DatabaseService.positions = {1: position}

    result = DatabaseService.getDividendCalendar("2024-01-01", "2024-06-30")

    assert len(result) == 1
    assert result[0]["type"] == "historical"
    assert result[0]["symbol"] == "AAPL"
    assert result[0]["total_amount"] == 5.0


@patch('sqlite3.connect')
def test_getDividendCalendar_projected_only(mock_connect):
    """Future date range should return only projected events."""
    mock_conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn

    mock_conn.execute.return_value.fetchall.side_effect = [
        # No historical dividends in range
        [],
        # _projectDividends query returns quarterly history
        [
            ("2024-01-15", 0.50),
            ("2024-04-15", 0.50),
            ("2024-07-15", 0.50),
            ("2024-10-15", 0.50),
        ],
    ]

    stock = Stock(stockid=1, symbol='AAPL', name='Apple Inc.', price=150.0)
    position = Position(stockid=1, quantity=10, stock=stock)
    DatabaseService.positions = {1: position}

    result = DatabaseService.getDividendCalendar("2025-01-01", "2025-12-31")

    assert len(result) > 0
    for event in result:
        assert event["type"] == "projected"
        assert event["symbol"] == "AAPL"


@patch('sqlite3.connect')
def test_getDividendCalendar_mixed(mock_connect):
    """Spanning range should return both historical and projected events, sorted by date."""
    mock_conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn

    mock_conn.execute.return_value.fetchall.side_effect = [
        # Historical dividends in range
        [("2025-01-15", 0.50, 1, "AAPL", "Apple Inc.")],
        # _projectDividends query: quarterly history
        [
            ("2024-01-15", 0.50),
            ("2024-04-15", 0.50),
            ("2024-07-15", 0.50),
            ("2024-10-15", 0.50),
            ("2025-01-15", 0.50),
        ],
    ]

    stock = Stock(stockid=1, symbol='AAPL', name='Apple Inc.', price=150.0)
    position = Position(stockid=1, quantity=5, stock=stock)
    DatabaseService.positions = {1: position}

    result = DatabaseService.getDividendCalendar("2025-01-01", "2025-12-31")

    types = {e["type"] for e in result}
    assert "historical" in types
    assert "projected" in types

    # Verify sorted by date
    dates = [e["date"] for e in result]
    assert dates == sorted(dates)


@patch('sqlite3.connect')
def test_getDividendCalendar_empty_portfolio(mock_connect):
    """Empty portfolio should return no events."""
    mock_conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value.fetchall.return_value = []

    DatabaseService.positions = {}

    result = DatabaseService.getDividendCalendar("2025-01-01", "2025-12-31")

    assert result == []


# ── API endpoint tests ───────────────────────────────────────────────

@patch('services.database_service.DatabaseService.getDividendCalendar')
def test_calendar_endpoint_success(mock_get_calendar):
    """GET /dividends/calendar should return 200 with valid data."""
    mock_get_calendar.return_value = [
        {
            "date": "2024-03-15",
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "amount_per_share": 0.50,
            "total_amount": 5.0,
            "type": "historical",
        },
        {
            "date": "2025-03-15",
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "amount_per_share": 0.50,
            "total_amount": 5.0,
            "type": "projected",
        },
    ]

    client = create_test_client()
    resp = client.get("/api/portfolio/dividends/calendar?start_date=2024-01-01&end_date=2025-12-31")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["events"]) == 2
    assert data["start_date"] == "2024-01-01"
    assert data["end_date"] == "2025-12-31"
    assert data["total_historical"] == 5.0
    assert data["total_projected"] == 5.0
    mock_get_calendar.assert_called_once_with("2024-01-01", "2025-12-31")


def test_calendar_endpoint_invalid_date():
    """GET /dividends/calendar with invalid date format should return 400."""
    client = create_test_client()
    resp = client.get("/api/portfolio/dividends/calendar?start_date=not-a-date&end_date=2025-12-31")

    assert resp.status_code == 400
    assert "Invalid date format" in resp.json()["detail"]


def test_calendar_endpoint_start_after_end():
    """GET /dividends/calendar with start_date > end_date should return 400."""
    client = create_test_client()
    resp = client.get("/api/portfolio/dividends/calendar?start_date=2026-01-01&end_date=2025-01-01")

    assert resp.status_code == 400
    assert "start_date must be before" in resp.json()["detail"]


@patch('services.database_service.DatabaseService.getDividendCalendar')
def test_calendar_endpoint_empty(mock_get_calendar):
    """GET /dividends/calendar with no events should return 200 with empty list."""
    mock_get_calendar.return_value = []

    client = create_test_client()
    resp = client.get("/api/portfolio/dividends/calendar?start_date=2025-01-01&end_date=2025-12-31")

    assert resp.status_code == 200
    data = resp.json()
    assert data["events"] == []
    assert data["total_historical"] == 0
    assert data["total_projected"] == 0
