import argparse
import math
from api.api import API
from portfolio_balancer.stock import Stock
from portfolio_balancer.file_loader import FileLoader

def total_value_portfolio(stocks: list[Stock]) -> float:
    result = 0.0
    for stock in stocks:
        result += stock.price * stock.quantity
    return result

def real_distribution(stocks: list[Stock], total_value: float) -> list[Stock]:
    for stock in stocks:
        stock.distribution_real = round((stock.price*stock.quantity)/total_value*100, 2)
    return stocks

# Rank the stocks by difference between the distribution_target and distribution_real
def stocks_ranking(stocks: list[Stock]) -> list[Stock]:
    result = sorted(stocks, key=lambda stock: (stock.distribution_target - stock.distribution_real))
    result.reverse()
    return result

def numbers_shares_to_buy(stocks: list[Stock], total_value: float, amount: int, min_amount: int):
    for stock in stocks:
        if stock.price > amount:
            continue
        target = (stock.distribution_target - stock.distribution_real)/100
        money_to_buy = target * (total_value+amount)
        tmp = math.floor(min(amount, money_to_buy)/stock.price)
        if (tmp*stock.price) < min_amount:
            continue
        amount = amount - (tmp*stock.price)

        print(stock.name, tmp, tmp*stock.price, " Stock price: ", stock.price)
    
    print("Leftover: ", math.floor(amount))

class Balancer:

    @staticmethod
    def balance(portfolio_file, amount, min_amount):
        stocks: list[Stock] = FileLoader.load_file(portfolio_file)
        stocks = API.load_shares(stocks=stocks)
        total_value = total_value_portfolio(stocks)
        stocks = real_distribution(stocks, total_value+amount)
        stocks = stocks_ranking(stocks)
        numbers_shares_to_buy(stocks, total_value, amount, min_amount)
        return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Balance portfolio')
    parser.add_argument('-f', '--portfolio_file', type=str, required=False, default="No file", help='JSON file containing the portfolio information')
    parser.add_argument('-a', '--amount', type=int, required=True, help='Amount to invest in the portfolio')
    parser.add_argument('-m', '--min_amount', type=int, required=False, default=100, help='Minimum amount that need to be invested per line')
    parser.add_argument('-fs', '--full_share', action='store_true', help='Only buy full share')
    args = parser.parse_args()
    Balancer.balance(args.portfolio_file, args.amount, args.min_amount)