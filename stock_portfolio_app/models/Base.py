import sqlite3
from config import DB_PATH as _DEFAULT_DB_PATH

class BaseModel:
    def __init__(self, table_name: str, db_path=None):
        self.db_path = db_path or _DEFAULT_DB_PATH
        self.table_name = table_name

    def execute_query(self, query, params=()):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            answer = cursor.execute(query, params).fetchall()
            connection.commit()
        return answer

    def fetchall(self):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute('SELECT * FROM ?', (self.table_name,))
            connection.commit()