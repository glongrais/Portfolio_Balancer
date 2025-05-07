import logging
import argparse
from services.portfolio_service import PortfolioService
from services.data_processing import DataProcessing
from models.Stock import Stock
from utils.file_utils import FileUtils
from utils.db_utils import initialize_database
from services.database_service import DatabaseService
from unittest.mock import MagicMock

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Stock Portfolio Application")
    parser.add_argument('--log-level', default='WARN', choices=['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'],
                        help='Set the logging level (default: WARN)')
    parser.add_argument('--amount', default=1000,
                        help='Set the amount in EUR to buy (default: 1000)')
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper()), 
                        format='%(levelname)s - %(name)s - %(message)s')
    initialize_database('../data/portfolio.db')
    DatabaseService.getStocks()
    DatabaseService.getPositions()
    DatabaseService.updatePortfolioPositionsPrice()
    DatabaseService.updateHistoricalStocksPortfolio("","")
    #DatabaseService.updateHistoricalDividendsPortfolio()
    FileUtils.refreshNumbers("/Users/guillaumelongrais/Library/Mobile Documents/com~apple~Numbers/Documents/Investissement.numbers")
    FileUtils.upsertTransactionsNumbers("/Users/guillaumelongrais/Library/Mobile Documents/com~apple~Numbers/Documents/Investissement.numbers")
    print(PortfolioService().calculatePortfolioValue())
    DataProcessing.fetch_current_year_dividends(["TTE.PA", "AAPL", "MC.PA"])
    DataProcessing.fetch_historical_dividends(["TTE.PA", "AAPL", "MC.PA"])
    PortfolioService.balancePortfolio(int(args.amount))
    # print(DatabaseService.portfolio)
