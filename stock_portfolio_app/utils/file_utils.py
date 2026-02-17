import logging
import os
import time

from numbers_parser import Document
from services.database_service import DatabaseService

logger = logging.getLogger(__name__)

DEFAULT_NUMBERS_FILE = (
    "/Users/guillaumel/Library/Mobile Documents/"
    "com~apple~Numbers/Documents/Investissement.numbers"
)

class FileUtils:

    @classmethod
    def importNumbers(cls, filename: str) -> None:

        # Value to adapt 
        SHEET = 'Dividends'
        TABLE = 'Repartition'
        SYMBOL = 0
        QUANTITY = 2
        DISTRIBUTION_TARGET = -1
        
        try:
            doc = Document(filename)
        except Exception as e:
            raise e
        
        table = doc.sheets[SHEET].tables[TABLE]
        table.delete_row(num_rows=table.num_header_rows, start_row=0)

        for row in table.rows(values_only=True):
            if row[0] is None:
                continue
            DatabaseService.addPosition(symbol=row[SYMBOL], quantity=int(row[QUANTITY]), distribution_target=row[DISTRIBUTION_TARGET]*100)

    @classmethod
    def refreshNumbers(cls, filename) -> None:

        # Value to adapt 
        SHEET = 'Dividends'
        TABLE = 'Repartition'
        SYMBOL = 0
        QUANTITY = 2
        AVERAGE_COST_BASIS = 8
        DISTRIBUTION_TARGET = -1
        
        try:
            doc = Document(filename)
        except Exception as e:
            raise e
        
        table = doc.sheets[SHEET].tables[TABLE]
        table.delete_row(num_rows=table.num_header_rows, start_row=0)

        for row in table.rows(values_only=True):
            if row[0] is None:
                continue
            DatabaseService.updatePosition(symbol=row[SYMBOL], quantity=int(row[QUANTITY]), average_cost_basis=row[AVERAGE_COST_BASIS], distribution_target=row[DISTRIBUTION_TARGET]*100)
    
    @classmethod
    def upsertTransactionsNumbers(cls, filename) -> None:

        # Value to adapt 
        SHEET = 'Transactions'
        TABLE = 'PEA'
        DATE = 0
        TYPE = 1
        SYMBOL = 2
        QUANTITY = 4
        PRICE = 5
        
        try:
            doc = Document(filename)
        except Exception as e:
            raise e
        
        table = doc.sheets[SHEET].tables[TABLE]
        table.delete_row(num_rows=table.num_header_rows, start_row=0)

        for row in table.rows():
            if row[0] is None:
                continue
            DatabaseService.upsertTransactions(rowid=row[0].row, symbol=row[SYMBOL].value, quantity=int(row[QUANTITY].value), price=row[PRICE].value, type=row[TYPE].value, date=row[DATE].value)

    @classmethod
    def get_numbers_file_path(cls) -> str:
        return os.environ.get("NUMBERS_FILE_PATH", DEFAULT_NUMBERS_FILE)

    @classmethod
    def refresh_from_numbers(cls) -> float:
        """
        Run refreshNumbers and upsertTransactionsNumbers from the configured Numbers file.
        Returns the total duration in seconds.
        """
        numbers_file = cls.get_numbers_file_path()
        logger.info(f"Refreshing data from Numbers file: {numbers_file}")

        start = time.perf_counter()
        cls.refreshNumbers(numbers_file)
        cls.upsertTransactionsNumbers(numbers_file)
        duration = time.perf_counter() - start

        logger.info(f"Numbers refresh completed in {duration:.2f}s")
        return duration
