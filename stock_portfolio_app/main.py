import logging
import argparse
import time
from config import DB_PATH, DEFAULT_NUMBERS_FILE
from services.portfolio_service import PortfolioService
from services.stock_api import StockAPI
from utils.file_utils import FileUtils
from utils.db_utils import initialize_database
from services.database_service import DatabaseService

logger = logging.getLogger(__name__)

def log_step(step_name, func, *args, **kwargs):
    start = time.perf_counter()
    result = func(*args, **kwargs)
    duration = time.perf_counter() - start
    logger.info(f"{step_name} took {duration:.2f} seconds")
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Stock Portfolio Application")
    parser.add_argument('--log-level', default='WARN', choices=['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'],
                        help='Set the logging level (default: WARN)')
    parser.add_argument('--amount', default=1000,
                        help='Set the amount in EUR to buy (default: 1000)')
    parser.add_argument('--numbers-file', default=DEFAULT_NUMBERS_FILE, help='Path to the Apple Numbers file')
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper()), 
                        format='%(levelname)s - %(name)s - %(message)s')
    log_step("Initialize database", initialize_database, DB_PATH)
    log_step("Get stocks", DatabaseService.getStocks)
    log_step("Get positions", DatabaseService.getPositions)
    log_step("Update portfolio positions price", DatabaseService.updatePortfolioPositionsPrice)
    log_step("Update historical stocks portfolio", DatabaseService.updateHistoricalStocksPortfolio, "", "")
    log_step("Update historical dividends portfolio", DatabaseService.updateHistoricalDividendsPortfolio)
    log_step("Refresh Numbers", FileUtils.refreshNumbers, args.numbers_file)
    log_step("Upsert transactions Numbers", FileUtils.upsertTransactionsNumbers, args.numbers_file)
    log_step("Calculate portfolio value", lambda: print(PortfolioService().calculatePortfolioValue()))
    log_step("Fetch current year dividends", StockAPI.get_current_year_dividends, ["TTE.PA", "AAPL", "MC.PA"])
    log_step("Fetch historical dividends", StockAPI.get_historical_dividends, ["TTE.PA", "AAPL", "MC.PA"])
    log_step("Balance portfolio", PortfolioService.balancePortfolio, int(args.amount))
    # print(DatabaseService.portfolio)
