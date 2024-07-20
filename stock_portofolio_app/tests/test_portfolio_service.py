import pytest
from services.database_service import DatabaseService
from services.portfolio_service import PortfolioService
from models.Stock import Stock
from models.Position import Position

@pytest.fixture
def setup_portfolio_service():
    # Reset the portfolio before each test
    DatabaseService.positions = {}
    yield

def test_calculatePortfolioValue_empty_portfolio(setup_portfolio_service):
    assert PortfolioService.calculatePortfolioValue() == 0

def test_calculatePortfolioValue_single_position(setup_portfolio_service):
    stock = Stock(stockid=1, symbol="AAPL", price=150.0)
    position = Position(stockid=1, quantity=10, stock=stock)
    DatabaseService.positions[1] = position
    assert PortfolioService.calculatePortfolioValue() == 1500

def test_calculatePortfolioValue_multiple_positions(setup_portfolio_service):
    stock1 = Stock(stockid=1, symbol="AAPL", price=150.0)
    position1 = Position(stockid=1, stock=stock1, quantity=10)
    stock2 = Stock(stockid=2, symbol="GOOGL", price=1000.0)
    position2 = Position(stockid=2, stock=stock2, quantity=5)
    DatabaseService.positions = {1: position1, 2: position2}
    assert PortfolioService.calculatePortfolioValue() == 6500