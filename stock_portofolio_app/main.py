import logging
from services.portfolio_service import PortfolioService
from services.data_processing import DataProcessing
from models.Stock import Stock
from utils.file_utils import load_numbers
from services.database_service import DatabaseService
from unittest.mock import MagicMock

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')
    # S = Stock()
    # S.update_prices()
    # load_numbers("/Users/guillaumelongrais/Library/Mobile Documents/com~apple~Numbers/Documents/Investissement.numbers")
    # print(PortfolioService().calculate_portfolio_value())
    # DataProcessing.fetch_historical_dividends(["TTE.PA"])
    # PortfolioService.balance_portfolio(3000)
    
    #print(DatabaseService.getStock(symbol="AAPL"))

    m = MagicMock()
    d = {'key_1': 'value'}
    m.__getitem__.side_effect = d.__getitem__

    print('key_1' in m)
    print(m['key_1'])

