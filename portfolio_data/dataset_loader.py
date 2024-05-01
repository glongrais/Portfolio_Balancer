import yfinance as yf
from pyspark.sql import SparkSession
import pandas as pd

def fetch_stock_data(tickers):
    stocks = yf.Tickers(tickers)
    tickers_list = tickers.split(',')
    data = None
    for ticker in tickers_list:
        hist = stocks.tickers[ticker].history(period="max")  # Fetches max historical data
        hist.reset_index(inplace=True)
        hist['ticker'] = ticker  # Add ticker column for reference
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
        .option("hoodie.datasource.write.partitionpath.field", "ticker") \
        .option("hoodie.datasource.write.operation", "upsert") \
        .option("hoodie.datasource.write.table.name", "stock_data") \
        .option("path", hudi_table_path) \
        .mode("append") \
        .save()

# Example usage
spark = create_spark_session()
df = fetch_stock_data("AAPL,MSFT")
df.rename(columns = {'Stock Splits':'Splits'}, inplace = True)
spark_df = spark.createDataFrame(df)
write_data_to_hudi(spark, spark_df, "/Users/guillaumelongrais/Documents/Code/Python/Portfolio_Balancing/stock_data")

