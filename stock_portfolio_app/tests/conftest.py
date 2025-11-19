import sys
import os

# Add the parent directory (stock_portfolio_app) to the Python path
# so that tests can import modules like 'models', 'services', etc.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

