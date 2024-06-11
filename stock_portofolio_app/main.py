from services.portfolio_service import PortfolioService
from models.Stock import Stock
from utils.file_utils import load_numbers

if __name__ == '__main__':
    S = Stock()
    S.update_prices()
    load_numbers("/Users/guillaumelongrais/Library/Mobile Documents/com~apple~Numbers/Documents/Investissement.numbers")
    print(PortfolioService().calculate_portfolio_value())