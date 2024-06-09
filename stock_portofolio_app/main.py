from services.portfolio_service import PortfolioService
from models.Stock import Stock

if __name__ == '__main__':
    Stock()
    c = PortfolioService()
    print(c.calculate_portfolio_value())