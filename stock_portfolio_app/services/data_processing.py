from external.stock_api import StockAPI

class DataProcessing:

    @classmethod
    def fetch_real_time_price(cls, symbol: str) -> float:
        """
        Fetches the real-time price of the given stock symbol.

        Parameters:
        - symbol: str

        Returns:
        - float: Real-time price
        """
        return StockAPI.get_current_price(symbol)

    @classmethod
    def fetch_historical_data(cls, symbol: str, start_date: str, end_date: str) -> list:
        """
        Fetches the historical data of the given stock symbol.

        Parameters:
        - symbol: str
        - start_date: str
        - end_date: str

        Returns:
        - list: Historical data points
        """
        return StockAPI.get_historical_data([symbol], start_date, end_date)[0]
    
    @classmethod
    def fetch_historical_data(cls, symbols: list, start_date: str, end_date: str) -> list:
        """
        Fetches the historical data of a set of stock symbols.

        Parameters:
        - symbols: list
        - start_date: str
        - end_date: str

        Returns:
        - list: Historical data points
        """
        return StockAPI.get_historical_data(symbols, start_date, end_date)
    
    @classmethod
    def fetch_historical_dividends(cls, symbols: list):
        """
        Fetches the historical dividend data of a set of stock symbols.

        Parameters:
        - symbols: list

        Returns:
        - dict: Historical dividend data points
        """
        dividends = StockAPI.get_historical_dividends(symbols)
        for d in dividends:
            print(d)
            print(list(dividends[d])[0].year)
        return 
