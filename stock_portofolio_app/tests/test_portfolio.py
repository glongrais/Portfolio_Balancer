import pytest
from models.Position import Position
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
def Position_data():
    stock = Stock(stockid=1, symbol='AAPL')
    return {'stockid': 1, 'quantity': 10, 'distribution_target': 10.0, 'distribution_real': 8.0, 'stock': stock}

def test_Position_creation(Position_data):
    position = Position(**Position_data)
    assert position.stockid == 1
    assert position.quantity == 10
    assert position.distribution_target == 10.0
    assert position.distribution_real == 8.0
    assert position.stock != None

def test_Position_default_values():
    position = Position(stockid=2, quantity=10)
    assert position.stockid == 2
    assert position.quantity == 10
    assert position.distribution_target == None
    assert position.distribution_real == 0.0
    assert position.stock == None

def test_dataclass_factory():
    cursor = MockCursor(description=[('stockid',), ('quantity',), ('distribution_target',), ('distribution_real',)])
    row = MockRow(values=[3, 10, 10.0, 5.0])
    position = Position.dataclass_factory(cursor, row.values)
    
    assert position.stockid == 3
    assert position.quantity == 10
    assert position.distribution_target == 10.0
    assert position.distribution_real == 5.0