import pytest
from models.Portfolio import Portfolio
from models.Stock import Stock
from typing import Any, List

# Mock classes to simulate cursor and row
class MockCursor:
    def __init__(self, description: List[Any]):
        self.description = description

class MockRow:
    def __init__(self, values: List[Any]):
        self.values = values

@pytest.fixture
def portfolio_data():
    stock = Stock(stockid=1, symbol='AAPL')
    return {'stockid': 1, 'quantity': 10, 'distribution_target': 10.0, 'distribution_real': 8.0, 'stock': stock}

def test_portfolio_creation(portfolio_data):
    portfolio = Portfolio(**portfolio_data)
    assert portfolio.stockid == 1
    assert portfolio.quantity == 10
    assert portfolio.distribution_target == 10.0
    assert portfolio.distribution_real == 8.0
    assert portfolio.stock != None

def test_portfolio_default_values():
    portfolio = Portfolio(stockid=2, quantity=10)
    assert portfolio.stockid == 2
    assert portfolio.quantity == 10
    assert portfolio.distribution_target == None
    assert portfolio.distribution_real == 0.0
    assert portfolio.stock == None

def test_dataclass_factory():
    cursor = MockCursor(description=[('stockid',), ('quantity',), ('distribution_target',), ('distribution_real',)])
    row = MockRow(values=[3, 10, 10.0, 5.0])
    portfolio = Portfolio.dataclass_factory(cursor, row.values)
    
    assert portfolio.stockid == 3
    assert portfolio.quantity == 10
    assert portfolio.distribution_target == 10.0
    assert portfolio.distribution_real == 5.0