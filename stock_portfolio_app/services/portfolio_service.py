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
    def balancePortfolio(cls, amount_to_buy, min_amount_to_buy=100):
        total_value = cls.calculatePortfolioValue()+amount_to_buy

        cls.updateRealDistribution()

        sorted_positions = dict(sorted(DatabaseService.positions.items(), key=lambda item: item[1].delta(), reverse=True))

        for position in sorted_positions.values():
            if position.stock.price > amount_to_buy:
                continue
            target = position.distribution_target/100 - round((position.stock.price*position.quantity)/(total_value), 4)
            money_to_buy = target * (total_value)
            tmp = math.floor(min(amount_to_buy, money_to_buy)/position.stock.price)
            if (tmp*position.stock.price) < min_amount_to_buy:
                continue
            amount_to_buy = amount_to_buy - (tmp*position.stock.price)
            print(position.stock.symbol, tmp, round(tmp*position.stock.price, 2), " Stock price: ", position.stock.price)       
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
