import yfinance as yf
from pyspark.sql import SparkSession
import pandas as pd

def fetch_stock_data(tickers):
    stocks = yf.Tickers(tickers)
    #tickers_list = tickers.split(',')
    data = None
    for ticker in tickers:
        hist = stocks.tickers[ticker].history(period="max")  # Fetches max historical data
        hist.reset_index(inplace=True)
        hist['Ticker'] = ticker  # Add ticker column for reference
        if data is None:
            data = hist
        else:
            data = pd.concat([data, hist])
            #data.append(hist)

    return data


def create_spark_session():
    return SparkSession.builder \
        .appName("Hudi Data Lake") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .config("spark.sql.extensions", "org.apache.spark.sql.hudi.HoodieSparkSessionExtension") \
        .config("spark.jars.packages", "org.apache.hudi:hudi-spark3.4-bundle_2.12:0.14.1") \
        .getOrCreate()

def write_data_to_hudi(data_frame, hudi_table_path):
    data_frame.write.format("hudi") \
        .option("hoodie.table.name", "stock_data") \
        .option("hoodie.datasource.write.recordkey.field", "Date") \
        .option("hoodie.datasource.write.precombine.field", "Date") \
        .option("hoodie.datasource.write.partitionpath.field", "Ticker") \
        .option("hoodie.datasource.write.operation", "upsert") \
        .option("hoodie.datasource.write.table.name", "stock_data") \
        .option("path", hudi_table_path) \
        .mode("append") \
        .save()

data_path = "/Users/guillaumelongrais/Documents/Code/Python/Portfolio_Balancing/stock_data"
portfolio_path = "/Users/guillaumelongrais/Documents/Code/Python/Portfolio_Balancing/portfolio_data"
# Example usage
spark = create_spark_session()
spark.sql(f"CREATE TABLE hudi_portfolio_data USING Hudi LOCATION '{portfolio_path}'")
tickers = spark.sql("SELECT symbol FROM hudi_portfolio_data")
tickers_list = tickers.select("symbol").rdd.flatMap(lambda x: x).collect()
df = fetch_stock_data(tickers_list)
df.rename(columns = {'Stock Splits':'Splits', 'Capital Gains':'Capital_Gains'}, inplace = True)
print(df.head(2))
spark_df = spark.createDataFrame(df)
write_data_to_hudi(spark_df, data_path)

