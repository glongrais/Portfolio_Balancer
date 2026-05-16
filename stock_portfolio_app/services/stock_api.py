import math
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

    EXCHANGE_CURRENCY_MAP = {
        "NMS": "USD", "NYQ": "USD", "NGM": "USD", "NCM": "USD", "ASE": "USD", "BTS": "USD", "PNK": "USD",
        "PAR": "EUR", "AMS": "EUR", "GER": "EUR", "MIL": "EUR", "BRU": "EUR", "LIS": "EUR", "MCE": "EUR",
        "STO": "SEK", "CPH": "DKK", "HEL": "EUR", "OSL": "NOK",
        "LSE": "GBP", "IOB": "GBP",
        "TYO": "JPY", "HKG": "HKD", "SHH": "CNY", "SHZ": "CNY",
        "TSX": "CAD", "ASX": "AUD",
    }

    @classmethod
    def search_stocks(cls, query: str, count: int = 10) -> list:
        lookup = yf.Lookup(query)
        df = lookup.stock
        if df is None or df.empty:
            return []
        results = []
        def _str(val, default=""):
            if val is None or (isinstance(val, float) and math.isnan(val)):
                return default
            return str(val)

        def _float(val, default=None):
            if val is None or (isinstance(val, float) and math.isnan(val)):
                return default
            return float(val)

        for symbol, row in df.head(count).iterrows():
            exchange = _str(row.get("exchange"))
            results.append({
                "symbol": symbol,
                "name": _str(row.get("shortName")),
                "exchange": exchange,
                "currency": cls.EXCHANGE_CURRENCY_MAP.get(exchange, ""),
                "price": _float(row.get("regularMarketPrice")),
                "quote_type": _str(row.get("quoteType"), "EQUITY"),
                "logo_url": f"https://api.elbstream.com/logos/symbol/{cls.LOGO_SYMBOL_MAP.get(symbol, symbol)}?format=png&size=128",
            })
        return results

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
            "previousClose": info.get("previousClose", 0) or 0,
            "dividendRate": info.get("dividendRate", 0) or 0,
            "dividendYield": info.get("dividendYield", 0) or 0,
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
    def get_splits(cls, symbols: list) -> dict:
        """
        Fetches stock split history for the given symbols.

        Parameters:
        - symbols: list of stock symbols

        Returns:
        - dict: symbol -> list of {"date": str, "ratio": float}
        """
        data = {}
        for symbol in symbols:
            try:
                splits = cls._get_ticker(symbol).splits
                if splits.empty:
                    continue
                data[symbol] = [
                    {"date": dt.strftime("%Y-%m-%d"), "ratio": float(ratio)}
                    for dt, ratio in splits.items()
                    if ratio > 0
                ]
            except Exception as e:
                cls.logger.warning(f"Failed to fetch splits for {symbol}: {e}")
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
    @cached(cache=TTLCache(maxsize=64, ttl=300))
    def get_intraday_data(cls, symbols_tuple: tuple) -> dict:
        """
        Fetches intra-day price data (5-min intervals) for the given symbols.
        Returns dict of symbol -> {"data": [...], "previous_close": float|None}.
        When market is closed, yfinance returns the last trading day's data.
        """
        result = {}
        with ThreadPoolExecutor() as executor:
            def fetch_intraday(symbol):
                try:
                    # Use 5d period to ensure we get the last trading day even on weekends
                    hist = cls._get_ticker(symbol).history(period="5d", interval="5m")
                    if hist.empty:
                        return symbol, {"data": [], "previous_close": None}
                    # Find trading days present in the data
                    trading_dates = sorted(hist.index.date)
                    unique_dates = sorted(set(trading_dates))
                    last_date = unique_dates[-1]
                    # Get previous trading day's close if available
                    previous_close = None
                    if len(unique_dates) >= 2:
                        prev_date = unique_dates[-2]
                        prev_day_data = hist[hist.index.date == prev_date]
                        if not prev_day_data.empty:
                            previous_close = round(prev_day_data["Close"].iloc[-1], 4)
                    # Keep only the last trading day's data
                    last_day = hist[hist.index.date == last_date]
                    points = []
                    for ts, row in last_day.iterrows():
                        points.append({
                            "timestamp": ts.strftime("%H:%M"),
                            "price": round(row["Close"], 4),
                        })
                    return symbol, {"data": points, "previous_close": previous_close}
                except Exception as e:
                    cls.logger.warning(f"Failed to fetch intraday data for {symbol}: {e}")
                    return symbol, {"data": [], "previous_close": None}

            futures = [executor.submit(fetch_intraday, s) for s in symbols_tuple]
            for future in as_completed(futures):
                symbol, payload = future.result()
                result[symbol] = payload
        return result

    @classmethod
    def get_current_year_dividends(cls, symbols: list):
        data = {}
        for symbol in symbols:
            info = cls._get_ticker(symbol).get_info()
            data[symbol] = info.get("dividendRate", 0.0) or 0.0
        return data
