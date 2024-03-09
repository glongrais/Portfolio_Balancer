import yfinance as yf
import requests_cache
from multiprocessing import Pool
from stock import Stock
session = requests_cache.CachedSession('yfinance.cache')
session.headers['User-agent'] = 'my-program/1.0'

def _load_share(stock: Stock):
    ticker = yf.Ticker(stock.symbol, session=session)
    stock.name = ticker.info["longName"]
    stock.price = ticker.info["currentPrice"]
    return stock


def load_shares(stocks: list[Stock]) -> list[Stock]:
    pool = Pool()
    stocks = pool.map(_load_share, stocks)
    return stocks