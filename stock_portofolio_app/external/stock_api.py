import yfinance as yf
from functools import lru_cache
import time

class StockPriceAPI:

    @classmethod
    @lru_cache()
    def _get_ticker(cls, symbol: str, ttl_hash=round(time.time() / 60)):
        del ttl_hash
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
 