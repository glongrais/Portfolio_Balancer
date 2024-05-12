from portfolio_balancer.stock import Stock
from pyspark.sql import SparkSession

def _create_spark_session():
    return SparkSession.builder \
        .appName("Hudi Data Lake") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .config("spark.sql.extensions", "org.apache.spark.sql.hudi.HoodieSparkSessionExtension") \
        .config("spark.jars.packages", "org.apache.hudi:hudi-spark3.4-bundle_2.12:0.14.1") \
        .getOrCreate()

def load_numbers() -> list[Stock]:

    spark_session = _create_spark_session()

    portfolio_path = "/Users/guillaumelongrais/Documents/Code/Python/Portfolio_Balancing/portfolio_data"
    spark_session.sql(f"CREATE TABLE hudi_portfolio_data USING Hudi LOCATION '{portfolio_path}'")
    df = spark_session.sql("SELECT symbol, quantity, distribution_target FROM hudi_portfolio_data")

    data = []
    for row in df.collect():
        data.append(Stock(symbol=row['symbol'], quantity=int(row['quantity']), distribution_target=row['distribution_target']*100))

    return data