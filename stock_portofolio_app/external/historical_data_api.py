import yfinance as yf

class HistoricalDataAPI:

    def get_historical_data(self, symbols: list, start_date: str, end_date: str) -> list:
        """
        Fetches historical data for the given stock symbol between start_date and end_date.
        
        Parameters:
        - symbol: str
        - start_date: str
        - end_date: str

        Returns:
        - list: Historical data points
        """
        stocks = yf.Tickers(symbols)
        data = []
        for ticker in symbols:
            hist = stocks.tickers[ticker].history(period="max")  # Fetches max historical data
            hist.reset_index(inplace=True)
            hist['Ticker'] = ticker  # Add ticker column for reference
            data.append(hist)

        return data
