import pytest
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
def stock_data():
    return {
        'stockid': 1,
        'symbol': 'AAPL',
        'name': 'Apple Inc.',
        'price': 150.0,
        'dividend': 0.82,
        'dividend_yield': 0.0055
    }

def test_stock_creation(stock_data):
    stock = Stock(**stock_data)
    assert stock.stockid == 1
    assert stock.symbol == 'AAPL'
    assert stock.name == 'Apple Inc.'
    assert stock.price == 150.0
    assert stock.dividend == 0.82
    assert stock.dividend_yield == 0.0055

def test_stock_default_values():
    stock = Stock(stockid=2, symbol='GOOGL')
    assert stock.stockid == 2
    assert stock.symbol == 'GOOGL'
    assert stock.name == ""
    assert stock.price == 0.0
    assert stock.dividend == 0.0
    assert stock.dividend_yield == 0.0

def test_dataclass_factory():
    cursor = MockCursor(description=[('stockid',), ('symbol',), ('name',), ('price',), ('dividend',), ('dividend_yield',)])
    row = MockRow(values=[3, 'MSFT', 'Microsoft Corp.', 250.0, 1.24, 0.0048])
    stock = Stock.dataclass_factory(cursor, row.values)
    
    assert stock.stockid == 3
    assert stock.symbol == 'MSFT'
    assert stock.name == 'Microsoft Corp.'
    assert stock.price == 250.0
    assert stock.dividend == 1.24
    assert stock.dividend_yield == 0.0048

def test_stock_update_dividend():
    stock = Stock(stockid=4, symbol='TSLA', name='Tesla Inc.', price=700.0)
    stock.dividend = 0.0
    stock.dividend_yield = 0.0
    assert stock.dividend == 0.0
    assert stock.dividend_yield == 0.0

    stock.dividend = 1.5
    stock.dividend_yield = 0.0021
    assert stock.dividend == 1.5
    assert stock.dividend_yield == 0.0021

def test_stock_partial_update():
    stock = Stock(stockid=5, symbol='AMZN', name='Amazon.com, Inc.', price=3300.0, dividend=0.0, dividend_yield=0.0)
    assert stock.dividend == 0.0
    assert stock.dividend_yield == 0.0

    stock.dividend = 2.0
    assert stock.dividend == 2.0
    assert stock.dividend_yield == 0.0
