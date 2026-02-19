from models.Base import BaseModel

class Transaction(BaseModel):

    def __init__(self, db_path=None):
        super().__init__('transactions', db_path)
        self.create_table()

    def create_table(self):
        self.execute_query('''
            CREATE TABLE IF NOT EXISTS transactions (
                    transactionid INTEGER PRIMARY KEY AUTOINCREMENT,
                    stockid       INTEGER NOT NULL,
                    quantity      INTEGER NULL    ,
                    price         REAL    NOT NULL,
                    type          TEXT    NULL    ,
                    datestamp     TEXT    NULL    ,
                    FOREIGN KEY (stockid) REFERENCES stocks (stockid)
            )
        ''')
