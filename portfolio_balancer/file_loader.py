from portfolio_balancer.stock import Stock
from portfolio_balancer.exception import UnsupportedFileTypeError
import os
import json
from portfolio_balancer.stock import Stock
from pyspark.sql import SparkSession

def create_spark_session():
    return SparkSession.builder \
        .appName("Hudi Data Lake") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .config("spark.sql.extensions", "org.apache.spark.sql.hudi.HoodieSparkSessionExtension") \
        .config("spark.jars.packages", "org.apache.hudi:hudi-spark3.4-bundle_2.12:0.14.1") \
        .getOrCreate()

def load_database() -> list[Stock]:

    spark_session = create_spark_session()

    portfolio_path = "/Users/guillaumelongrais/Documents/Code/Python/Portfolio_Balancing/portfolio_data"
    spark_session.sql(f"CREATE TABLE hudi_portfolio_data USING Hudi LOCATION '{portfolio_path}'")
    df = spark_session.sql("SELECT symbol, quantity, distribution_target FROM hudi_portfolio_data")

    data = []
    for row in df.collect():
        data.append(Stock(symbol=row['symbol'], quantity=int(row['quantity']), distribution_target=row['distribution_target']*100))

    return data

def load_json(filename: str) -> list[Stock]:
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"The file {filename} was not found.") from e
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Error decoding JSON from the file {filename}.", e.doc, e.pos)

    return [Stock(**i) for i in data]

class FileLoader:

    @staticmethod
    def load_file(filename: str) -> list[Stock]:
        try:
            if filename.lower().endswith('.json'):
                return load_json(filename)
            elif filename == 'No file':
                return load_database()
            else:
                _, file_extension = os.path.splitext(filename)
                raise UnsupportedFileTypeError(file_extension)
        except UnsupportedFileTypeError as e:
            raise e