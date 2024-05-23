from numbers_parser import Document
from portfolio_balancer.stock import Stock
from pyspark.sql import SparkSession
import pandas as pd

def load_numbers(filename: str) -> list[Stock]:

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

    datas = []
    for row in table.rows(values_only=True):
        if row[0] is None:
            continue
        datas.append(Stock(symbol=row[SYMBOL], quantity=int(row[QUANTITY]), distribution_target=row[DISTRIBUTION_TARGET]))

    df =  pd.DataFrame([data.__dict__ for data in datas])
    df['date'] = pd.Timestamp.today()#.strftime('%Y-%m-%d')

    return df

def create_spark_session():
    return SparkSession.builder \
        .appName("Hudi Data Lake") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .config("spark.sql.extensions", "org.apache.spark.sql.hudi.HoodieSparkSessionExtension") \
        .config("spark.jars.packages", "org.apache.hudi:hudi-spark3.4-bundle_2.12:0.14.1") \
        .getOrCreate()

def write_data_to_hudi(data_frame, hudi_table_path):
    data_frame.write.format("hudi") \
        .option("hoodie.table.name", "portfolio_data") \
        .option("hoodie.datasource.write.recordkey.field", "symbol") \
        .option("hoodie.datasource.write.precombine.field", "date") \
        .option("hoodie.datasource.write.operation", "upsert") \
        .option("hoodie.datasource.write.table.name", "portfolio_data") \
        .option("path", hudi_table_path) \
        .mode("append") \
        .save()

portfolio = load_numbers("/Users/guillaumelongrais/Library/Mobile Documents/com~apple~Numbers/Documents/Investissement.numbers")
spark = create_spark_session()
spark_df = spark.createDataFrame(portfolio)
write_data_to_hudi(spark_df, "/Users/guillaumelongrais/Documents/Code/Python/Portfolio_Balancing/portfolio_data")
