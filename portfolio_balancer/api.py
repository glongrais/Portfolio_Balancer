import yfinance as yf
import requests_cache
from multiprocessing import Pool
from portfolio_balancer.stock import Stock
# Create a cached session
session = requests_cache.CachedSession('yfinance.cache')
session.headers['User-agent'] = 'my-program/1.0'

# Function to set up the session in each process
def init_pool_processes():
    global session
    session = requests_cache.CachedSession('yfinance.cache')
    session.headers['User-agent'] = 'my-program/1.0'

# Function to load a single share
def load_share(stock: Stock):
    ticker = yf.Ticker(stock.symbol)
    info = ticker.info
    if "currentPrice" in info.keys():
        stock.price = info["currentPrice"]
    else:
        stock.price = info["previousClose"]
    stock.name = info.get("longName", "")
    return stock

class API:

    @staticmethod
    def load_shares(stocks: list[Stock]) -> list[Stock]:
        with Pool(initializer=init_pool_processes) as pool:
            stocks = pool.map(load_share, stocks)
        return stocks