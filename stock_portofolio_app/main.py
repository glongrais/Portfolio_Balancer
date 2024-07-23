import logging
from services.portfolio_service import PortfolioService
from services.data_processing import DataProcessing
from models.Stock import Stock
from utils.file_utils import FileUtils
from utils.db_utils import initialize_database
from services.database_service import DatabaseService
from unittest.mock import MagicMock

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')
    # S = Stock()
    # S.update_prices()
    initialize_database('data/portfolio.db')
    DatabaseService.getStocks()
    DatabaseService.getPositions()
    #FileUtils.load_numbers("/Users/guillaumelongrais/Library/Mobile Documents/com~apple~Numbers/Documents/Investissement.numbers")
    print(PortfolioService().calculatePortfolioValue())
    # DataProcessing.fetch_historical_dividends(["TTE.PA"])
    PortfolioService.balancePortfolio(3000)
    # print(DatabaseService.portfolio)
    
