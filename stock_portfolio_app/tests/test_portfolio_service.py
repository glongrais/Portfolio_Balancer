import pytest
from unittest.mock import patch
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

def test_calculatePortfolioValue_updated_prices(setup_portfolio_service):
    stock = Stock(stockid=1, symbol="AAPL", price=150.0)
    position = Position(stockid=1, stock=stock, quantity=10)
    DatabaseService.positions[1] = position
    assert PortfolioService.calculatePortfolioValue() == 1500
    
    # Update the stock price
    stock.price = 200.0
    assert PortfolioService.calculatePortfolioValue() == 2000

@patch('services.portfolio_service.PortfolioService.calculatePortfolioValue')
@patch('services.portfolio_service.PortfolioService.updateRealDistribution')
@patch('services.database_service.DatabaseService.positions', new_callable=dict)
@patch('builtins.print')
def test_balancePortfolio(mock_print, mock_positions, mock_update_real_distribution, mock_calculate_portfolio_value, setup_portfolio_service):
    # Setup mock return values
    mock_calculate_portfolio_value.return_value = 10000

    # Create mock positions
    stock1 = Stock(stockid=1, symbol='AAPL', price=150)
    position1 = Position(stockid=1, quantity=10, distribution_target=20.0, distribution_real=10.0, stock=stock1)
    
    stock2 = Stock(stockid=2, symbol='GOOG', price=100)
    position2 = Position(stockid=2, quantity=5, distribution_target=30.0, distribution_real=25.0, stock=stock2)
    
    mock_positions[1] = position1
    mock_positions[2] = position2

    # Call the method under test
    PortfolioService.balancePortfolio(amount_to_buy=1000, min_amount_to_buy=50)

    # Assertions
    mock_update_real_distribution.assert_called_once()
    mock_calculate_portfolio_value.assert_called_once()

    # Check the printed output
    mock_print.assert_any_call('AAPL', 4, 600.0, ' Stock price: ', 150)
    mock_print.assert_any_call('GOOG', 4, 400.0, ' Stock price: ', 100)
    mock_print.assert_any_call('Leftover: ', 0)

@patch('services.portfolio_service.PortfolioService.calculatePortfolioValue')
@patch('services.portfolio_service.PortfolioService.updateRealDistribution')
@patch('services.database_service.DatabaseService.positions', new_callable=dict)
@patch('builtins.print')
def test_balancePortfolio_leftover_no_purchase(mock_print, mock_positions, mock_update_real_distribution, mock_calculate_portfolio_value):
    # Setup mock return values
    mock_calculate_portfolio_value.return_value = 10000

    # Create mock positions
    stock1 = Stock(stockid=1, symbol='AAPL', price=150)
    position1 = Position(stockid=1, quantity=10, distribution_target=20.0, distribution_real=10.0, stock=stock1)
    
    stock2 = Stock(stockid=2, symbol='GOOG', price=200)
    position2 = Position(stockid=2, quantity=5, distribution_target=30.0, distribution_real=25.0, stock=stock2)
    
    mock_positions[1] = position1
    mock_positions[2] = position2

    # Call the method under test with a small amount to buy
    PortfolioService.balancePortfolio(amount_to_buy=100, min_amount_to_buy=50)

    # Assertions
    mock_update_real_distribution.assert_called_once()
    mock_calculate_portfolio_value.assert_called_once()

    # Ensure leftover amount is handled correctly
    mock_print.assert_any_call('Leftover: ', 100)

@patch('services.portfolio_service.PortfolioService.calculatePortfolioValue')
@patch('services.portfolio_service.PortfolioService.updateRealDistribution')
@patch('services.database_service.DatabaseService.positions', new_callable=dict)
@patch('builtins.print')
def test_balancePortfolio_leftover_one_purchase(mock_print, mock_positions, mock_update_real_distribution, mock_calculate_portfolio_value):
    # Setup mock return values
    mock_calculate_portfolio_value.return_value = 10000

    # Create mock positions
    stock1 = Stock(stockid=1, symbol='AAPL', price=150)
    position1 = Position(stockid=1, quantity=10, distribution_target=20.0, distribution_real=10.0, stock=stock1)
    
    stock2 = Stock(stockid=2, symbol='GOOG', price=100)
    position2 = Position(stockid=2, quantity=5, distribution_target=30.0, distribution_real=25.0, stock=stock2)
    
    mock_positions[1] = position1
    mock_positions[2] = position2

    # Call the method under test with a small amount to buy
    PortfolioService.balancePortfolio(amount_to_buy=120, min_amount_to_buy=50)

    # Assertions
    mock_update_real_distribution.assert_called_once()
    mock_calculate_portfolio_value.assert_called_once()

    # Ensure leftover amount is handled correctly
    mock_print.assert_any_call('Leftover: ', 20)

@patch('services.portfolio_service.PortfolioService.calculatePortfolioValue')
@patch('services.portfolio_service.PortfolioService.updateRealDistribution')
@patch('services.database_service.DatabaseService.positions', new_callable=dict)
@patch('builtins.print')
def test_balancePortfolio_leftover_multiple_purchase(mock_print, mock_positions, mock_update_real_distribution, mock_calculate_portfolio_value):
    # Setup mock return values
    mock_calculate_portfolio_value.return_value = 10000

    # Create mock positions
    stock1 = Stock(stockid=1, symbol='AAPL', price=150)
    position1 = Position(stockid=1, quantity=10, distribution_target=20.0, distribution_real=10.0, stock=stock1)
    
    stock2 = Stock(stockid=2, symbol='GOOG', price=100)
    position2 = Position(stockid=2, quantity=5, distribution_target=30.0, distribution_real=25.0, stock=stock2)
    
    mock_positions[1] = position1
    mock_positions[2] = position2

    # Call the method under test with a small amount to buy
    PortfolioService.balancePortfolio(amount_to_buy=950, min_amount_to_buy=50)

    # Assertions
    mock_update_real_distribution.assert_called_once()
    mock_calculate_portfolio_value.assert_called_once()

    # Ensure leftover amount is handled correctly
    mock_print.assert_any_call('Leftover: ', 50)

@patch("models.Position.Position")
def test_updateRealDistribution_empty_portfolio(mock_Position, setup_portfolio_service):
    PortfolioService.updateRealDistribution()
    mock_Position.distribution_real.assert_not_called()

def test_updateRealDistribution_single_position(setup_portfolio_service):
    stock = Stock(stockid=1, symbol="AAPL", price=150.0)
    position = Position(stockid=1, stock=stock, quantity=10)
    DatabaseService.positions[1] = position

    PortfolioService.updateRealDistribution()
    assert position.distribution_real == 100.0

def test_updateRealDistribution_multiple_positions(setup_portfolio_service):
    stock1 = Stock(stockid=1, symbol="AAPL", price=150.0)
    position1 = Position(stockid=1, stock=stock1, quantity=10)
    stock2 = Stock(stockid=2, symbol="GOOGL", price=1000.0)
    position2 = Position(stockid=2, stock=stock2, quantity=5)
    DatabaseService.positions = {1: position1, 2: position2}

    PortfolioService.updateRealDistribution()
    assert position1.distribution_real == round((150.0 * 10) / ((150.0 * 10) + (1000.0 * 5)) * 100, 2)
    assert position2.distribution_real == round((1000.0 * 5) / ((150.0 * 10) + (1000.0 * 5)) * 100, 2)

def test_updateRealDistribution_updated_prices(setup_portfolio_service):
    stock = Stock(stockid=1, symbol="AAPL", price=150.0)
    position = Position(stockid=1, stock=stock, quantity=10)
    DatabaseService.positions[1] = position

    PortfolioService.updateRealDistribution()
    assert position.distribution_real == 100.0
    
    # Update the stock price
    stock.price = 200.0
    PortfolioService.updateRealDistribution()
    assert position.distribution_real == 100.0