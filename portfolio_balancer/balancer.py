import argparse
from api import load_shares
from stock import Stock
from file_loader import load_file

def _total_value(stocks: list[Stock]) -> float:
    result = 0.0
    for stock in stocks:
        result += stock.price * stock.quantity
    return result

def _real_distribution(stocks: list[Stock], total_value: float) -> list[Stock]:
    for stock in stocks:
        stock.distribution_real = round((stock.price*stock.quantity)/total_value*100, 2)
    return stocks

# Rank the stocks by difference between the distribution_target and distribution_real
def _stocks_ranking(stocks: list[Stock]) -> list[Stock]:
    return sorted(stocks, key=lambda stock: abs(stock.distribution_target - stock.distribution_real))


def main(args):
    stocks: list[Stock] = load_file(args.portfolio_file)
    stocks = load_shares(stocks)
    total_value = _total_value(stocks)
    stocks = _real_distribution(stocks, total_value)
    stocks = _stocks_ranking(stocks)
    print(stocks)
    return 0
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Balance portfolio')
    parser.add_argument('-f', '--portfolio_file', type=str, required=True, help='JSON file containing the portfolio information')
    parser.add_argument('-a', '--amount', type=int, required=True, help='Amount to invest in the portfolio')
    parser.add_argument('-m', '--min_amount', type=int, required=False, default=100, help='Minimum amount that need to be invested per line')
    parser.add_argument('-fs', '--full_share', action='store_true', help='Only buy full share')
    args = parser.parse_args()
    main(args)