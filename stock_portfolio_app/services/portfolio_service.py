# services/portfolio_service.py
from models.Position import Position
from models.Stock import Stock
from models.Transaction import Transaction
from services.database_service import DatabaseService
from services.data_processing import DataProcessing
import math
from datetime import datetime
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
        """
        Balances the portfolio by buying stocks according to their target distribution.

        Args:
            amount_to_buy (float): The total amount of money to be used for buying stocks.
            min_amount_to_buy (float, optional): The minimum amount of money to be spent on a single stock purchase. Defaults to 100.

        Returns:
            None

        This method calculates the total value of the portfolio after adding the amount to buy, updates the real distribution of the portfolio,
        and then iterates through the sorted positions to buy stocks according to their target distribution. It ensures that the amount spent
        on each stock is above the minimum amount to buy and prints the details of each purchase. Finally, it prints the leftover amount.
        """
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
            DatabaseService.updatePosition(symbol=position.stock.symbol, distribution_real=position.distribution_real)

    @classmethod
    def getDividendCalendar(cls):
        return
    
    @classmethod
    def getTotalYearlyDividend(cls):
        total_dividend = 0
        for position in DatabaseService.positions.values():
            dividend_rate = DataProcessing.fetch_current_year_dividends([position.stock.symbol])[position.stock.symbol]
            total_dividend += dividend_rate * position.quantity
        return total_dividend

    @classmethod
    def get_transaction_history(cls) -> list:
        """
        Retrieves the transaction history.

        Returns:
        - list: Transaction history
        """
        transaction = Transaction()
        return transaction.fetchall('SELECT * FROM transactions')
    
    @classmethod
    def getPortfolioValueHistory(cls) -> list:
        """
        Retrieves the portfolio value history.

        Returns:
        - list: Portfolio value history
        """
        return DatabaseService.getPortfolioValueHistory()
    
    @classmethod
    def getDividendTotal(cls) -> float:
        """
        Retrieves the total dividends received.

        Returns:
        - float: Total dividends
        """
        return DatabaseService.getDividendTotal()

    @classmethod
    def getDividendYearToDate(cls) -> float:
        """
        Calculates the total dividends received year-to-date.

        Returns:
        - float: Year-to-date dividends
        """
        current_year = str(datetime.now().year)
        return DatabaseService.getDividendYearToDate(current_year)

    @classmethod
    def getDividendYearlyForecast(cls) -> float:
        """
        Calculates the forecasted yearly dividends based on current positions
        and their expected dividend rates.

        Returns:
        - float: Forecasted yearly dividends
        """
        total_forecast = 0.0
        for position in DatabaseService.positions.values():
            dividend_rate = DataProcessing.fetch_current_year_dividends(
                [position.stock.symbol]
            )[position.stock.symbol]
            total_forecast += dividend_rate * position.quantity
        return round(total_forecast, 2)

    @classmethod
    def getNextDividend(cls) -> dict:
        """
        Retrieves information about the next expected dividend payment.

        Returns:
        - dict: Contains stockid and dividend_rate
        """
        return DatabaseService.getNextDividendInfo()

    @classmethod
    def getPositionById(cls, stockid: int) -> Position:
        """
        Retrieves a position by its stock ID.

        Args:
        - stockid: The stock ID of the position

        Returns:
        - Position: The position object, or None if not found
        """
        return DatabaseService.positions.get(stockid)
