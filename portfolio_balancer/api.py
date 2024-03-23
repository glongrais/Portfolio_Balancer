import yfinance as yf
import requests_cache
from multiprocessing import Pool
from portfolio_balancer.stock import Stock
session = requests_cache.CachedSession('yfinance.cache')
session.headers['User-agent'] = 'my-program/1.0'

def _load_share(stock: Stock):
    ticker = yf.Ticker(stock.symbol, session=session)
    if "currentPrice" in ticker.info.keys():
        stock.price = ticker.info["currentPrice"]
    else:
        stock.price = ticker.info["previousClose"]
    stock.name = ticker.info["longName"]
    return stock


def load_shares(stocks: list[Stock]) -> list[Stock]:
    pool = Pool()
    stocks = pool.map(_load_share, stocks)
    return stocks