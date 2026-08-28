"""
CompuCog Universal Temporal Reasoning Engine - Core Engine
Implements streaming two-pass architecture for building 6-1-6 windows
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Counter as CounterType
from collections import Counter, defaultdict
from dataclasses import dataclass


@dataclass
class SymbolEvent:
    """Single symbol event"""
    timestamp: int
    entity: str
    symbol: str
    genome: str
    value: float
    metadata: Optional[Dict] = None


@dataclass
class Window:
    """6-1-6 context window"""
    timestamp: int
    entity: str
    center_symbol: str
    context_before: List[str]  # 6 symbols before
    context_after: List[str]   # 6 symbols after
    genome: str


class UnifiedEngine:
    """
    Core temporal reasoning engine with streaming two-pass architecture.
    
    MEMORY EFFICIENT: Uses sliding window buffer (13 events max in memory)
    instead of loading all events.
    """
    
    def __init__(
        self,
        domain: str,
        data_dir: str = "data",
        window_size: int = 6,
        top_k: int = 5
    ):
        self.domain = domain
        self.data_dir = Path(data_dir)
        self.window_size = window_size
        self.top_k = top_k
        
        # File paths
        self.symbols_file = self.data_dir / "symbols" / f"{domain}_symbols.jsonl"
        self.windows_file = self.data_dir / "windows" / f"{domain}_windows.jsonl"
        self.resonance_file = self.data_dir / "resonance" / f"{domain}_resonance.jsonl"
        self.clouds_file = self.data_dir / "clouds" / f"{domain}_clouds.jsonl"
        
        # Lifetime counts (small, kept in memory)
        self.lifetime_counts: Dict[str, Dict[int, CounterType[str]]] = defaultdict(
            lambda: defaultdict(Counter)
        )
        
        # Context map for resonance (small, kept in memory)
        self.context_map: Dict[str, Dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        
        # Statistics
        self.stats = {
            "symbols_processed": 0,
            "windows_created": 0,
            "resonance_computed": 0,
            "clouds_built": 0
        }
    
    def process(self) -> int:
        """
        Two-pass streaming process:
        1. Build lifetime counts (streaming)
        2. Build windows + resonance (streaming)
        
        Returns: Number of windows created
        """
        print(f"[Engine] Starting two-pass processing for domain: {self.domain}")
        
        # PASS 1: Build lifetime counts
        print("[Engine] Pass 1: Building lifetime counts...")
        self._build_lifetime_counts_streaming()
        
        # PASS 2: Build windows + resonance
        print("[Engine] Pass 2: Building windows and resonance...")
        self._build_windows_streaming()
        
        # Build context clouds
        print("[Engine] Building context clouds...")
        self._build_clouds()
        
        print(f"[Engine] Processing complete. Stats: {self.stats}")
        return self.stats["windows_created"]
    
    def _build_lifetime_counts_streaming(self):
        """
        PASS 1: Stream through symbols file and build lifetime counts.
        Uses sliding window buffer (13 events max in memory).
        """
        if not self.symbols_file.exists():
            print(f"[Engine] No symbols file found: {self.symbols_file}")
            return
        
        buffer: List[SymbolEvent] = []
        buffer_size = 2 * self.window_size + 1  # 13 for 6-1-6
        
        with open(self.symbols_file, 'r') as f:
            for line in f:
                event_data = json.loads(line)
                event = SymbolEvent(**event_data)
                
                buffer.append(event)
                self.stats["symbols_processed"] += 1
                
                # Process center event when buffer is full
                if len(buffer) == buffer_size:
                    center_idx = self.window_size
                    center_event = buffer[center_idx]
                    
                    # Update lifetime counts for center symbol
                    for offset in range(-self.window_size, self.window_size + 1):
                        if offset == 0:
                            continue
                        context_event = buffer[center_idx + offset]
                        self.lifetime_counts[center_event.symbol][offset][context_event.symbol] += 1
                    
                    # Slide buffer forward
                    buffer.pop(0)
        
        # Finalize lifetime counts to top-K
        print(f"[Engine] Finalizing lifetime counts (top-{self.top_k})...")
        for symbol in self.lifetime_counts:
            for offset in self.lifetime_counts[symbol]:
                # Keep only top-K most frequent symbols at this offset
                top_symbols = self.lifetime_counts[symbol][offset].most_common(self.top_k)
                self.lifetime_counts[symbol][offset] = Counter(dict(top_symbols))
    
    def _build_windows_streaming(self):
        """
        PASS 2: Stream through symbols file again and build windows + resonance.
        Writes windows and resonance immediately to disk.
        """
        if not self.symbols_file.exists():
            return
        
        buffer: List[SymbolEvent] = []
        buffer_size = 2 * self.window_size + 1
        
        # Prepare output files
        self.windows_file.parent.mkdir(parents=True, exist_ok=True)
        self.resonance_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.symbols_file, 'r') as f_in, \
             open(self.windows_file, 'w') as f_windows, \
             open(self.resonance_file, 'w') as f_resonance:
            
            for line in f_in:
                event_data = json.loads(line)
                event = SymbolEvent(**event_data)
                
                buffer.append(event)
                
                # Build window when buffer is full
                if len(buffer) == buffer_size:
                    center_idx = self.window_size
                    center_event = buffer[center_idx]
                    
                    # Build 6-1-6 window
                    context_before = [buffer[i].symbol for i in range(center_idx)]
                    context_after = [buffer[i].symbol for i in range(center_idx + 1, buffer_size)]
                    
                    window = Window(
                        timestamp=center_event.timestamp,
                        entity=center_event.entity,
                        center_symbol=center_event.symbol,
                        context_before=context_before,
                        context_after=context_after,
                        genome=center_event.genome
                    )
                    
                    # Write window immediately
                    f_windows.write(json.dumps(window.__dict__) + '\n')
                    self.stats["windows_created"] += 1
                    
                    # Compute resonance for this window
                    resonance = self._compute_resonance(window)
                    
                    # Write resonance immediately
                    resonance_data = {
                        "timestamp": window.timestamp,
                        "entity": window.entity,
                        "center_symbol": window.center_symbol,
                        "resonance": resonance
                    }
                    f_resonance.write(json.dumps(resonance_data) + '\n')
                    self.stats["resonance_computed"] += 1
                    
                    # Slide buffer forward
                    buffer.pop(0)
    
    def _compute_resonance(self, window: Window) -> Dict[str, float]:
        """
        Compute position-weighted resonance for a window.
        Closer positions have stronger weights (1.0 at ±1, 0.2 at ±6).
        """
        resonance: Dict[str, float] = defaultdict(float)
        
        # Process context_before (positions -6 to -1)
        for i, symbol in enumerate(window.context_before):
            offset = -(self.window_size - i)  # -6, -5, ..., -1
            weight = 1.0 - (abs(offset) - 1) / (self.window_size - 1) * 0.8
            resonance[symbol] += weight
            
            # Update context map
            self.context_map[window.center_symbol][symbol] += weight
        
        # Process context_after (positions +1 to +6)
        for i, symbol in enumerate(window.context_after):
            offset = i + 1  # +1, +2, ..., +6
            weight = 1.0 - (abs(offset) - 1) / (self.window_size - 1) * 0.8
            resonance[symbol] += weight
            
            # Update context map
            self.context_map[window.center_symbol][symbol] += weight
        
        return dict(resonance)
    
    def _build_clouds(self):
        """
        Build context clouds from resonance data.
        Groups symbols by resonance strength.
        """
        self.clouds_file.parent.mkdir(parents=True, exist_ok=True)
        
        threshold = 0.5  # Minimum resonance to be in a cloud
        
        with open(self.clouds_file, 'w') as f:
            for center_symbol, context in self.context_map.items():
                # Filter by threshold
                cloud_members = {
                    symbol: strength
                    for symbol, strength in context.items()
                    if strength >= threshold
                }
                
                if cloud_members:
                    cloud_data = {
                        "center_symbol": center_symbol,
                        "cloud_members": cloud_members,
                        "cloud_size": len(cloud_members)
                    }
                    f.write(json.dumps(cloud_data) + '\n')
                    self.stats["clouds_built"] += 1
    
    def get_statistics(self) -> Dict:
        """Return processing statistics"""
        return {
            **self.stats,
            "domain": self.domain,
            "window_size": self.window_size,
            "top_k": self.top_k,
            "unique_symbols": len(self.lifetime_counts),
            "unique_clouds": len(self.context_map)
        }


if __name__ == "__main__":
    # Test the engine
    engine = UnifiedEngine(domain="finance", window_size=6, top_k=5)
    window_count = engine.process()
    print(f"\nEngine test complete. Created {window_count} windows.")
    print(f"Statistics: {engine.get_statistics()}")
