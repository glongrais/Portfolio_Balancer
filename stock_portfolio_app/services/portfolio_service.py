# services/portfolio_service.py
from models.Position import Position
from models.Stock import Stock
from models.Transaction import Transaction
from services.database_service import DatabaseService
from services.stock_api import StockAPI
import math
from datetime import datetime
from cachetools import cached, TTLCache

class PortfolioService:

    @classmethod
    def calculatePortfolioValue(cls, portfolio_id: int = 1) -> float:
        """
        Calculates the total value of the portfolio.

        :param portfolio_id: The portfolio to calculate value for.
        :return: Total portfolio value
        """
        total_value = 0
        for position in DatabaseService.getPositionsForPortfolio(portfolio_id).values():
            total_value += position.quantity * position.stock.price
        return round(total_value)

    @classmethod
    def balancePortfolio(cls, amount_to_buy, min_amount_to_buy=100, portfolio_id: int = 1):
        """
        Balances the portfolio by buying stocks according to their target distribution.
        """
        total_value = cls.calculatePortfolioValue(portfolio_id) + amount_to_buy

        cls.updateRealDistribution(portfolio_id)

        portfolio_positions = DatabaseService.getPositionsForPortfolio(portfolio_id)
        sorted_positions = dict(sorted(portfolio_positions.items(), key=lambda item: item[1].delta(), reverse=True))

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
    def updateRealDistribution(cls, portfolio_id: int = 1):
        total_value = cls.calculatePortfolioValue(portfolio_id)

        for position in DatabaseService.getPositionsForPortfolio(portfolio_id).values():
            position.distribution_real = round((position.stock.price * position.quantity)/total_value*100, 2)
            DatabaseService.updatePosition(symbol=position.stock.symbol, distribution_real=position.distribution_real, portfolio_id=portfolio_id)

    @classmethod
    def getDividendCalendar(cls):
        return

    @classmethod
    def getTotalYearlyDividend(cls, portfolio_id: int = 1):
        total_dividend = 0
        for position in DatabaseService.getPositionsForPortfolio(portfolio_id).values():
            dividend_rate = StockAPI.get_current_year_dividends([position.stock.symbol])[position.stock.symbol]
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
    def getPortfolioValueHistory(cls, portfolio_id: int = 1) -> list:
        """
        Retrieves the portfolio value history.

        :param portfolio_id: The portfolio to fetch history for.
        Returns:
        - list: Portfolio value history
        """
        return DatabaseService.getPortfolioValueHistory(portfolio_id)

    @classmethod
    def getDividendTotal(cls, portfolio_id: int = 1) -> float:
        """
        Retrieves the total dividends received.

        :param portfolio_id: The portfolio to calculate dividends for.
        Returns:
        - float: Total dividends
        """
        return DatabaseService.getDividendTotal(portfolio_id)

    @classmethod
    def getDividendYearToDate(cls, portfolio_id: int = 1) -> float:
        """
        Calculates the total dividends received year-to-date.

        :param portfolio_id: The portfolio to calculate dividends for.
        Returns:
        - float: Year-to-date dividends
        """
        current_year = str(datetime.now().year)
        return DatabaseService.getDividendYearToDate(current_year, portfolio_id)

    @classmethod
    def getDividendYearlyForecast(cls, portfolio_id: int = 1) -> float:
        """
        Calculates the forecasted yearly dividends based on current positions
        and their expected dividend rates.

        :param portfolio_id: The portfolio to calculate forecast for.
        Returns:
        - float: Forecasted yearly dividends
        """
        total_forecast = 0.0
        for position in DatabaseService.getPositionsForPortfolio(portfolio_id).values():
            dividend_rate = StockAPI.get_current_year_dividends(
                [position.stock.symbol]
            )[position.stock.symbol]
            total_forecast += dividend_rate * position.quantity
        return round(total_forecast, 2)

    @classmethod
    def getNextDividend(cls, portfolio_id: int = 1) -> dict:
        """
        Retrieves information about the next expected dividend payment.

        :param portfolio_id: The portfolio to check dividends for.
        Returns:
        - dict: Contains stockid and dividend_rate
        """
        return DatabaseService.getNextDividendInfo(portfolio_id)

    @classmethod
    def getPositionById(cls, stockid: int, portfolio_id: int = 1) -> Position:
        """
        Retrieves a position by its stock ID.

        :param stockid: The stock ID of the position
        :param portfolio_id: The portfolio to look in.
        Returns:
        - Position: The position object, or None if not found
        """
        return DatabaseService.getPositionsForPortfolio(portfolio_id).get(stockid)
