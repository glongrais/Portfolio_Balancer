# services/portfolio_service.py
from models.Portfolio import Portfolio
from models.Stock import Stock
from models.Transaction import Transaction
#from models.historical_stock import HistoricalStock
#from external.stock_price_api import StockPriceAPI
import time
import math
from functools import lru_cache

class PortfolioService:

    @classmethod
    @lru_cache()
    def calculate_portfolio_value(cls, ttl_hash=round(time.time() / 60)) -> float:
        """
        Calculates the total value of the portfolio.

        Returns:
        - float: Total portfolio value
        """
        portfolio = Portfolio()
        portfolio_entries = portfolio.execute_query(
            '''
            SELECT stocks.stockid, portfolio.quantity, stocks.price FROM portfolio LEFT JOIN stocks ON portfolio.stockid = stocks.stockid 
            '''
        )
        if portfolio_entries == None:
            return 0
        else:
            total_value = sum(quantity * price for stockid, quantity, price in portfolio_entries)
            return round(total_value)

    @classmethod
    def balance_portfolio(cls, amount_to_buy, min_amount_to_buy=100):
        total_value = cls.calculate_portfolio_value()+amount_to_buy

        cls.update_real_distribution()

        portfolio = Portfolio()
        stocks = portfolio.execute_query(
            '''
                SELECT stocks.stockid, stocks.symbol, stocks.price, portfolio.quantity, portfolio.distribution_target, portfolio.distribution_real, (portfolio.distribution_target - portfolio.distribution_real) as delta FROM portfolio LEFT JOIN stocks ON portfolio.stockid = stocks.stockid ORDER BY delta DESC
            '''
        )
        for stockid, symbol, price, quantity, distribution_target, distribution_real, delta in stocks:
            if price > amount_to_buy:
                continue
            target = distribution_target/100 - round((price*quantity)/(total_value), 4)
            money_to_buy = target * (total_value)
            tmp = math.floor(min(amount_to_buy, money_to_buy)/price)
            if (tmp*price) < min_amount_to_buy:
                continue
            amount_to_buy = amount_to_buy - (tmp*price)
            print(symbol, tmp, round(tmp*price, 2), " Stock price: ", price)
        
        print("Leftover: ", math.floor(amount_to_buy))

    @classmethod
    def update_real_distribution(cls):
        total_value = cls.calculate_portfolio_value()

        portfolio = Portfolio()
        portfolio_entries = portfolio.execute_query(
            '''
            SELECT stocks.stockid, portfolio.quantity, stocks.price FROM portfolio LEFT JOIN stocks ON portfolio.stockid = stocks.stockid 
            '''
        )

        if portfolio_entries == None:
            return
        else:
            for stockid, quantity, price in portfolio_entries:
                distribution_real = round((price*quantity)/total_value*100, 2)
                portfolio.execute_query('UPDATE portfolio SET distribution_real = ? WHERE stockid = ?', (distribution_real, stockid,))

    @classmethod
    def get_transaction_history(cls) -> list:
        """
        Retrieves the transaction history.

        Returns:
        - list: Transaction history
        """
        transaction = Transaction()
        return transaction.fetchall('SELECT * FROM transactions')
