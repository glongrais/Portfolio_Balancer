import pytest
import json
from unittest import mock
from portfolio_balancer.stock import Stock
from portfolio_balancer.file_loader import FileLoader
from portfolio_balancer.exception import UnsupportedFileTypeError

def test_load_valid_file():
    valid_data = [{'symbol': 'ABC', 'quantity': 100, 'distribution_target': 80.0}, {'symbol': 'XYZ', 'quantity': 200, 'distribution_target': 20.0}]
    with mock.patch('builtins.open', mock.mock_open(read_data=json.dumps(valid_data))):
        result = FileLoader.load_file('dummy_file.json')
        assert len(result) == 2
        assert all(isinstance(stock, Stock) for stock in result)
        assert result[0].symbol == 'ABC'
        assert result[1].quantity == 200
        assert result[1].distribution_target == 20.0

def test_load_invalid_json():
    with mock.patch('builtins.open', mock.mock_open(read_data='invalid json')):
        with pytest.raises(json.JSONDecodeError):
            FileLoader.load_file('dummy_file.json')

def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        FileLoader.load_file('non_existent_file.json')

def test_empty_file():
    with mock.patch('builtins.open', mock.mock_open(read_data='[]')):
        result = FileLoader.load_file('dummy_file.json')
        assert result == []

def test_file_with_partial_invalid_data():
    mixed_data = [{'name': 'ABC', 'price': 100}, {'invalid': 'data'}]
    with mock.patch('builtins.open', mock.mock_open(read_data=json.dumps(mixed_data))):
        with pytest.raises(TypeError):
            FileLoader.load_file('dummy_file.json')

def test_non_json_file():
    non_json_data = 'Some random text'
    with mock.patch('builtins.open', mock.mock_open(read_data=non_json_data)):
        with pytest.raises(json.JSONDecodeError):
            FileLoader.load_file('dummy_file.json')

def test_file_type_not_supported():
    with pytest.raises(UnsupportedFileTypeError):
        FileLoader.load_file('non_supported_file.aaa')