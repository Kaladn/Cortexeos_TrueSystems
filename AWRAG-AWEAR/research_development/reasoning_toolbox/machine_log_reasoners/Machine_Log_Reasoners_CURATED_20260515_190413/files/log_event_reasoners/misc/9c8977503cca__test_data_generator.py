#!/usr/bin/env python3
"""
Generate test OHLCV data for CompuCog testing
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_ohlcv_data(
    symbol: str = "AAPL",
    days: int = 30,
    start_price: float = 150.0,
    output_file: str = None
):
    """
    Generate synthetic OHLCV data for testing.
    
    Args:
        symbol: Stock symbol
        days: Number of days of data
        start_price: Starting price
        output_file: Output CSV file path
    """
    np.random.seed(42)  # Reproducible
    
    data = []
    current_price = start_price
    start_date = datetime.now() - timedelta(days=days)
    
    for day in range(days):
        timestamp = int((start_date + timedelta(days=day)).timestamp())
        
        # Generate OHLCV with realistic patterns
        daily_change = np.random.normal(0, 2)  # Mean 0, std 2
        
        open_price = current_price
        close_price = current_price + daily_change
        high_price = max(open_price, close_price) + abs(np.random.normal(0, 1))
        low_price = min(open_price, close_price) - abs(np.random.normal(0, 1))
        volume = int(np.random.uniform(5_000_000, 50_000_000))
        
        data.append({
            "timestamp": timestamp,
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": volume
        })
        
        current_price = close_price
    
    df = pd.DataFrame(data)
    
    if output_file is None:
        output_file = f"{symbol}_test_data.csv"
    
    df.to_csv(output_file, index=False)
    print(f"Generated {len(df)} rows of OHLCV data for {symbol}")
    print(f"Saved to: {output_file}")
    print(f"\nSample data:")
    print(df.head())
    
    return output_file


if __name__ == "__main__":
    # Generate test data for AAPL
    generate_ohlcv_data(symbol="AAPL", days=30, output_file="test_data/AAPL.csv")
    
    # Generate test data for MSFT
    generate_ohlcv_data(symbol="MSFT", days=30, start_price=300.0, output_file="test_data/MSFT.csv")
