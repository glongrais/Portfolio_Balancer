import yfinance as yf
from cachetools import cached, TTLCache

class StockAPI:

    @classmethod
    @cached(cache=TTLCache(maxsize=1024, ttl=60))
    def _get_ticker(cls, symbol: str):
        return yf.Ticker(symbol)

    @classmethod
    def get_current_price(cls, symbol: str) -> float:
        """
        Fetches the current price of the given stock symbol.
        
        Parameters:
        - symbol: str

        Returns:
        - float: Current price
        """
        ticker = cls._get_ticker(symbol)
        info = ticker.info
        if "currentPrice" in info.keys():
            return info["currentPrice"]
        else:
            return info["previousClose"]
        #stock.name = info.get("longName", "")

    @classmethod
    def get_historical_data(cls, symbols: list, start_date: str, end_date: str) -> list:
        """
        Fetches historical data for the given stock symbol between start_date and end_date.
        
        Parameters:
        - symbol: str
        - start_date: str
        - end_date: str

        Returns:
        - list: Historical data points
        """
        data = []
        for symbol in symbols:
            hist = cls._get_ticker(symbol).history(period="max")  # Fetches max historical data
            hist.reset_index(inplace=True)
            hist['Ticker'] = symbol  # Add ticker column for reference
            data.append(hist)

        return data
    
    @classmethod
    def get_historical_dividends(cls, symbols: list):
        data = {}
        for symbol in symbols:
            data[symbol] = cls._get_ticker(symbol).get_dividends().to_dict()
        return data
    
    @classmethod
    def get_current_year_dividends(cls, symbols: list):
        data = {}
        for symbol in symbols:
            data[symbol] = cls._get_ticker(symbol).get_info()["dividendRate"]
        return data 
 