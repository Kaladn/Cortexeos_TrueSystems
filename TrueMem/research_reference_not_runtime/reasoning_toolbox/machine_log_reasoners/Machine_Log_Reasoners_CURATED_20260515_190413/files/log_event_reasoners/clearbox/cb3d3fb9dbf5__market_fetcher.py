"""
Market Data Fetcher
Fetches historical market data from yfinance
"""

import yfinance as yf


class MarketFetcher:
    """Fetches market data from yfinance"""
    
    def __init__(self, config):
        self.config = config
    
    def fetch(self, ticker, period="2y"):
        """
        Fetch historical market data
        
        Args:
            ticker: Stock/crypto ticker symbol
            period: Time period (e.g., "2y", "5y", "max")
        
        Returns:
            list: List of market data dictionaries, or empty list if failed
        """
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period)
            
            if df.empty:
                return []
            
            data = []
            for date, row in df.iterrows():
                data.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume'])
                })
            
            return data
            
        except Exception as e:
            print(f"Error fetching data for {ticker}: {str(e)}")
            return []
