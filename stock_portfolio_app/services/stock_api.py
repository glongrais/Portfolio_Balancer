import yfinance as yf
from cachetools import cached, TTLCache
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

class StockAPI:

    logger = logging.getLogger(__name__)

    # Ticker symbol overrides for the logo API when it uses a different symbol
    LOGO_SYMBOL_MAP = {
        "STLAP.PA": "STLA",
    }

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

        ex_div_raw = info.get("exDividendDate")
        ex_dividend_date = None
        if ex_div_raw is not None:
            if isinstance(ex_div_raw, (int, float)):
                from datetime import datetime
                try:
                    ex_dividend_date = datetime.fromtimestamp(ex_div_raw).strftime('%Y-%m-%d')
                except (ValueError, TypeError, OSError):
                    pass
            elif hasattr(ex_div_raw, 'strftime'):
                ex_dividend_date = ex_div_raw.strftime('%Y-%m-%d')
            elif isinstance(ex_div_raw, str):
                ex_dividend_date = ex_div_raw

        return {
            "currentPrice": info.get("currentPrice", info.get("previousClose")),
            "longName": info.get("longName", ""),
            "symbol": symbol,
            "currency": info.get("currency", ""),
            "marketCap": info.get("marketCap", None),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "country": info.get("country", ""),
            "logo_url": f"https://api.elbstream.com/logos/symbol/{cls.LOGO_SYMBOL_MAP.get(symbol, symbol)}?format=png&size=128",
            "quoteType": info.get("quoteType", "EQUITY"),
            "exDividendDate": ex_dividend_date,
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
            raw = cls._get_ticker(symbol).get_dividends().to_dict()
            data[symbol] = {t.strftime('%Y-%m-%d'): v for t, v in raw.items()}
        return data
    
    @classmethod
    @cached(cache=TTLCache(maxsize=64, ttl=300))
    def get_fx_rate(cls, from_currency: str, to_currency: str = "EUR") -> float:
        """
        Fetches the current FX rate between two currencies.

        Parameters:
        - from_currency: Source currency code (e.g. 'USD')
        - to_currency: Target currency code (default 'EUR')

        Returns:
        - float: Exchange rate (e.g. 0.92 for USD→EUR)
        """
        if from_currency.upper() == to_currency.upper():
            return 1.0
        try:
            ticker = cls._get_ticker(f"{from_currency}{to_currency}=X")
            info = ticker.info
            return info.get("regularMarketPrice", 1.0) or 1.0
        except Exception as e:
            cls.logger.warning(f"Failed to fetch FX rate {from_currency}/{to_currency}: {e}")
            return 1.0

    @classmethod
    def get_historical_fx_rates(cls, pair: str, start_date: str) -> list:
        """
        Fetches historical FX rates for a currency pair.

        Parameters:
        - pair: Currency pair (e.g. 'USDEUR')
        - start_date: Start date for history (YYYY-MM-DD)

        Returns:
        - list: List of (date_str, rate) tuples
        """
        try:
            ticker = cls._get_ticker(f"{pair}=X")
            hist = ticker.history(start=start_date)
            hist.reset_index(inplace=True)
            return [
                (row['Date'].strftime('%Y-%m-%d'), row['Close'])
                for _, row in hist.iterrows()
            ]
        except Exception as e:
            cls.logger.warning(f"Failed to fetch historical FX rates for {pair}: {e}")
            return []

    @classmethod
    def get_current_year_dividends(cls, symbols: list):
        data = {}
        for symbol in symbols:
            info = cls._get_ticker(symbol).get_info()
            data[symbol] = info.get("dividendRate", 0.0) or 0.0
        return data
