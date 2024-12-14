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
    logging.basicConfig(level=logging.WARN, format='%(levelname)s - %(name)s - %(message)s')
    initialize_database('data/portfolio.db')
    DatabaseService.getStocks()
    DatabaseService.getPositions()
    DatabaseService.updatePortfolioPositionsPrice()
    #FileUtils.importNumbers("/Users/guillaumelongrais/Library/Mobile Documents/com~apple~Numbers/Documents/Investissement.numbers")
    FileUtils.refreshNumbers("/Users/guillaumelongrais/Library/Mobile Documents/com~apple~Numbers/Documents/Investissement.numbers")
    print(PortfolioService().calculatePortfolioValue())
    DataProcessing.fetch_current_year_dividends(["TTE.PA", "AAPL", "MC.PA"])
    PortfolioService.balancePortfolio(1740)
    # print(DatabaseService.portfolio)
    
