# services/portfolio_service.py
from models.Position import Position
from models.Stock import Stock
from models.Transaction import Transaction
from services.database_service import DatabaseService
import math
from cachetools import cached, TTLCache

class PortfolioService:

    @classmethod
    #@cached(cache=TTLCache(maxsize=1024, ttl=60))
    def calculatePortfolioValue(cls) -> float:
        """
        Calculates the total value of the portfolio.

        :return: Total portfolio value
        """
        total_value = 0
        for position in DatabaseService.positions.values():
            total_value += position.quantity * position.stock.price
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
    def updateRealDistribution(cls):
        total_value = cls.calculatePortfolioValue()

        for position in DatabaseService.positions.values():
            position.distribution_real = round((position.stock.price * position.quantity)/total_value*100, 2)

    @classmethod
    def get_transaction_history(cls) -> list:
        """
        Retrieves the transaction history.

        Returns:
        - list: Transaction history
        """
        transaction = Transaction()
        return transaction.fetchall('SELECT * FROM transactions')
