import yfinance as yf
from cachetools import cached, TTLCache
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

class StockAPI:

    logger = logging.getLogger(__name__)

    @classmethod
    @cached(cache=TTLCache(maxsize=1024, ttl=60))
    def _get_ticker(cls, symbol: str):
        cls.logger.debug(f"Fetching data for {symbol} from yfinance")
        return yf.Ticker(symbol)

    @classmethod
    def get_current_price(cls, symbol: str) -> dict:
        """
        Fetches the current price and additional information of the given stock symbol.
        
        Parameters:
        - symbol: str

        Returns:
        - dict: Current price and additional information
        """
        ticker = cls._get_ticker(symbol)
        info = ticker.info
        return {
            "currentPrice": info.get("currentPrice", info.get("previousClose")),
            "longName": info.get("longName", ""),
            "symbol": symbol,
            "currency": info.get("currency", ""),
            "marketCap": info.get("marketCap", None),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "country": info.get("country", "")
        }

    @classmethod
    def get_ticker_info(cls, symbol: str) -> dict:
        """
        Fetches all available information for the given stock symbol.

        Parameters:
        - symbol: str

        Returns:
        - dict: All available information
        """
        ticker = cls._get_ticker(symbol)
        return ticker.info

    @classmethod
    def get_historical_data(cls, symbols: list, start_date: str, end_date: str=None) -> list:
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
        with ThreadPoolExecutor() as executor:
            def fetch_history(symbol):
                hist = cls._get_ticker(symbol).history(start=start_date, end=end_date)
                hist.reset_index(inplace=True)
                hist['Ticker'] = symbol
                return hist

            futures = [executor.submit(fetch_history, symbol) for symbol in symbols]
            data = [future.result() for future in as_completed(futures)]

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
