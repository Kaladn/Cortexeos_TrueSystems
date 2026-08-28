"""
CompuCog Finance Adapter
Converts OHLCV financial data to symbol events using genome mapping
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class FinanceAdapter:
    """
    Converts financial OHLCV data to symbol events.
    Uses genome file to map price ranges to symbols.
    """
    
    def __init__(self, genome_path: str, output_dir: str = "data/symbols"):
        self.genome_path = Path(genome_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load genome
        self.genome = self._load_genome()
        
        # Statistics
        self.stats = {
            "rows_processed": 0,
            "events_created": 0,
            "errors": 0
        }
    
    def _load_genome(self) -> Dict:
        """Load genome mapping file"""
        if not self.genome_path.exists():
            raise FileNotFoundError(f"Genome file not found: {self.genome_path}")
        
        with open(self.genome_path, 'r') as f:
            genome = json.load(f)
        
        print(f"[FinanceAdapter] Loaded genome: {genome.get('name', 'Unknown')}")
        return genome
    
    def ingest(self, source: str, entity: str = None) -> int:
        """
        Ingest OHLCV data from CSV file.
        
        Args:
            source: Path to CSV file with columns: timestamp, open, high, low, close, volume
            entity: Entity name (e.g., "AAPL"). If None, derived from filename.
        
        Returns:
            Number of events created
        """
        source_path = Path(source)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source}")
        
        # Derive entity from filename if not provided
        if entity is None:
            entity = source_path.stem.upper()
        
        print(f"[FinanceAdapter] Ingesting {source} for entity: {entity}")
        
        # Read CSV
        try:
            df = pd.read_csv(source)
        except Exception as e:
            print(f"[FinanceAdapter] Error reading CSV: {e}")
            self.stats["errors"] += 1
            return 0
        
        # Validate columns
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            print(f"[FinanceAdapter] Missing required columns. Expected: {required_cols}")
            self.stats["errors"] += 1
            return 0
        
        # Output file
        output_file = self.output_dir / f"finance_symbols.jsonl"
        
        # Process each row
        with open(output_file, 'a') as f:  # Append mode for multiple ingestions
            for _, row in df.iterrows():
                try:
                    # Convert OHLCV to symbols
                    events = self._ohlcv_to_symbols(row, entity)
                    
                    # Write events
                    for event in events:
                        f.write(json.dumps(event) + '\n')
                        self.stats["events_created"] += 1
                    
                    self.stats["rows_processed"] += 1
                    
                except Exception as e:
                    print(f"[FinanceAdapter] Error processing row: {e}")
                    self.stats["errors"] += 1
        
        print(f"[FinanceAdapter] Ingestion complete. Stats: {self.stats}")
        return self.stats["events_created"]
    
    def _ohlcv_to_symbols(self, row: pd.Series, entity: str) -> List[Dict]:
        """
        Convert OHLCV row to symbol events.
        
        Maps:
        - Open/High/Low/Close → Price symbols (using genome ranges)
        - Volume → Volume symbol (using genome ranges)
        """
        events = []
        timestamp = int(row['timestamp'])
        
        # Price fields
        price_fields = {
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close']
        }
        
        for field, value in price_fields.items():
            symbol = self._map_price_to_symbol(value)
            events.append({
                "timestamp": timestamp,
                "entity": entity,
                "symbol": f"{field}_{symbol}",
                "genome": "finance_ohlcv",
                "value": float(value),
                "metadata": {"field": field}
            })
        
        # Volume
        volume_symbol = self._map_volume_to_symbol(row['volume'])
        events.append({
            "timestamp": timestamp,
            "entity": entity,
            "symbol": f"volume_{volume_symbol}",
            "genome": "finance_ohlcv",
            "value": float(row['volume']),
            "metadata": {"field": "volume"}
        })
        
        return events
    
    def _map_price_to_symbol(self, price: float) -> str:
        """Map price to symbol using genome ranges"""
        # Simple bucketing for now (can be enhanced with genome ranges)
        if price < 50:
            return "LOW"
        elif price < 100:
            return "MED"
        elif price < 200:
            return "HIGH"
        else:
            return "VHIGH"
    
    def _map_volume_to_symbol(self, volume: float) -> str:
        """Map volume to symbol using genome ranges"""
        # Simple bucketing for now
        if volume < 1_000_000:
            return "LOW"
        elif volume < 10_000_000:
            return "MED"
        elif volume < 50_000_000:
            return "HIGH"
        else:
            return "VHIGH"
    
    def get_statistics(self) -> Dict:
        """Return ingestion statistics"""
        return self.stats


if __name__ == "__main__":
    # Test the adapter
    print("FinanceAdapter test mode")
    print("Create a genome file and CSV to test ingestion")
