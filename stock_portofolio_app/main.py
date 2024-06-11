from services.portfolio_service import PortfolioService
from models.Stock import Stock
from utils.file_utils import load_numbers

if __name__ == '__main__':
    Stock()
    load_numbers("/Users/guillaumelongrais/Library/Mobile Documents/com~apple~Numbers/Documents/Investissement.numbers")
    c = PortfolioService()
    print(c.calculate_portfolio_value())