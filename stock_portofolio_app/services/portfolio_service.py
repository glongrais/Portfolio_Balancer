# services/portfolio_service.py
from models.Portfolio import Portfolio
from models.Stock import Stock
#from models.transaction import Transaction
#from models.historical_stock import HistoricalStock
#from external.stock_price_api import StockPriceAPI
from external.historical_data_api import HistoricalDataAPI

class PortfolioService:
    def __init__(self):
        self.portfolio = Portfolio()
        self.stock = Stock()
        #self.transaction = Transaction()
        #self.historical_stock = HistoricalStock()
        #self.stock_price_api = StockPriceAPI(api_key='YOUR_API_KEY')
        self.historical_data_api = HistoricalDataAPI()

    def calculate_portfolio_value(self) -> float:
        """
        Calculates the total value of the portfolio.

        Returns:
        - float: Total portfolio value
        """
        portfolio_entries = self.portfolio.execute_query(
            '''
            SELECT stocks.stockid, portfolio.quantity, stocks.price FROM portfolio LEFT JOIN stocks ON portfolio.stockid = stocks.stockid 
            '''
        )
        if portfolio_entries == None:
            return 0
        else:
            total_value = sum(quantity * price for stockid, quantity, price in portfolio_entries)
            return total_value

    def get_transaction_history(self) -> list:
        """
        Retrieves the transaction history.

        Returns:
        - list: Transaction history
        """
        return self.transaction.fetchall('SELECT * FROM transactions')
