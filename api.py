import yfinance as yf
import requests_cache
session = requests_cache.CachedSession('yfinance.cache')
session.headers['User-agent'] = 'my-program/1.0'

def load_shares() -> dict:
    tickers = yf.Tickers('msft aapl goog', session=session)
    return tickers.tickers