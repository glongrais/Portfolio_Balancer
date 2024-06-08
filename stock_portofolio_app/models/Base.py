import sqlite3

class BaseModel:
    def __init__(self, table_name: str, db_path='data/portfolio.db'):
        self.db_path = db_path
        self.table_name = table_name

    def execute_query(self, query, params=()):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute(query, params)
            connection.commit()

    def fetchall(self):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute('SELECT * FROM ?', (self.table_name,))
            connection.commit()