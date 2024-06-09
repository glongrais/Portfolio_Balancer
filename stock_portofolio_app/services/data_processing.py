# services/data_processing.py
#from external.stock_price_api import StockPriceAPI
from external.historical_data_api import HistoricalDataAPI

class DataProcessing:
    def __init__(self, historical_data_api: HistoricalDataAPI):
        #self.stock_price_api = stock_price_api
        self.historical_data_api = historical_data_api

#    def fetch_real_time_price(self, symbol: str) -> float:
        """
        Fetches the real-time price of the given stock symbol.

        Parameters:
        - symbol: str

        Returns:
        - float: Real-time price
        """
#        return self.stock_price_api.get_current_price(symbol)

    def fetch_historical_data(self, symbol: str, start_date: str, end_date: str) -> list:
        """
        Fetches the historical data of the given stock symbol.

        Parameters:
        - symbol: str
        - start_date: str
        - end_date: str

        Returns:
        - list: Historical data points
        """
        return self.historical_data_api.get_historical_data([symbol], start_date, end_date)[0]
    
    def fetch_historical_data(self, symbols: list, start_date: str, end_date: str) -> list:
        """
        Fetches the historical data of a set of stock symbols.

        Parameters:
        - symbols: list
        - start_date: str
        - end_date: str

        Returns:
        - list: Historical data points
        """
        return self.historical_data_api.get_historical_data(symbols, start_date, end_date)
