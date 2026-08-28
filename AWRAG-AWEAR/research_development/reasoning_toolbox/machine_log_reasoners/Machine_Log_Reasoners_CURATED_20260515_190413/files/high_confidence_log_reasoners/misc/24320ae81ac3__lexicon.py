"""
CompuCog Global Lexicon - The Spine of 6-1-6

This is the CORE POWER of 6-1-6.
Not the windows. Not the resonance.
THE LEXICON.

Tracks:
- Every word seen across ALL documents
- Lifetime frequency (cumulative count)
- Lifetime adjacency (what appears near what)
- Stable symbol assignment (word → symbol, permanent)

This is pre-thought memory.
No reasoning. No interpretation. Just counting.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import Counter, defaultdict


class GlobalLexicon:
    """
    The spine of 6-1-6.
    
    Tracks word frequencies and adjacencies across ALL documents.
    Assigns stable symbols that persist forever.
    
    This is NOT per-document.
    This is NOT per-domain.
    This is GLOBAL LIFETIME MEMORY.
    """
    
    def __init__(self, lexicon_file: str = "data/lexicon.jsonl"):
        self.lexicon_file = Path(lexicon_file)
        self.lexicon_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Core data structures
        self.word_to_symbol: Dict[str, str] = {}  # word → stable symbol
        self.symbol_to_word: Dict[str, str] = {}  # symbol → word (reverse lookup)
        self.word_frequency: Counter = Counter()  # word → lifetime count
        self.word_adjacency: Dict[str, Counter] = defaultdict(Counter)  # word → {neighbor: count}
        
        # Statistics
        self.total_words_seen = 0
        self.total_documents_processed = 0
        self.unique_words = 0
        
        # Load existing lexicon if it exists
        self._load()
    
    def _load(self):
        """Load existing lexicon from disk"""
        if not self.lexicon_file.exists():
            print("[Lexicon] No existing lexicon found. Starting fresh.")
            return
        
        print(f"[Lexicon] Loading from {self.lexicon_file}")
        
        with open(self.lexicon_file, 'r') as f:
            for line in f:
                entry = json.loads(line)
                
                if entry['type'] == 'word':
                    word = entry['word']
                    symbol = entry['symbol']
                    freq = entry['frequency']
                    
                    self.word_to_symbol[word] = symbol
                    self.symbol_to_word[symbol] = word
                    self.word_frequency[word] = freq
                
                elif entry['type'] == 'adjacency':
                    word = entry['word']
                    neighbor = entry['neighbor']
                    count = entry['count']
                    
                    self.word_adjacency[word][neighbor] = count
                
                elif entry['type'] == 'stats':
                    self.total_words_seen = entry['total_words_seen']
                    self.total_documents_processed = entry['total_documents_processed']
                    self.unique_words = entry['unique_words']
        
        print(f"[Lexicon] Loaded {len(self.word_to_symbol)} words, {self.total_documents_processed} documents")
    
    def _save(self):
        """Save lexicon to disk (append-only)"""
        # Clear file and rewrite (simpler than incremental for now)
        with open(self.lexicon_file, 'w') as f:
            # Write word entries
            for word, symbol in self.word_to_symbol.items():
                entry = {
                    'type': 'word',
                    'word': word,
                    'symbol': symbol,
                    'frequency': self.word_frequency[word]
                }
                f.write(json.dumps(entry) + '\n')
            
            # Write adjacency entries
            for word, neighbors in self.word_adjacency.items():
                for neighbor, count in neighbors.items():
                    entry = {
                        'type': 'adjacency',
                        'word': word,
                        'neighbor': neighbor,
                        'count': count
                    }
                    f.write(json.dumps(entry) + '\n')
            
            # Write stats
            stats = {
                'type': 'stats',
                'total_words_seen': self.total_words_seen,
                'total_documents_processed': self.total_documents_processed,
                'unique_words': self.unique_words
            }
            f.write(json.dumps(stats) + '\n')
    
    def register_word(self, word: str) -> str:
        """
        Register a word in the lexicon.
        
        If word is new, assign a stable symbol.
        If word exists, return existing symbol.
        
        Args:
            word: The word to register
        
        Returns:
            Stable symbol for this word
        """
        # Normalize word (lowercase, strip)
        word = word.lower().strip()
        
        if not word:
            return "EMPTY"
        
        # Check if word already exists
        if word in self.word_to_symbol:
            return self.word_to_symbol[word]
        
        # New word - assign symbol
        symbol = self._assign_symbol(word)
        self.word_to_symbol[word] = symbol
        self.symbol_to_word[symbol] = word
        self.unique_words += 1
        
        print(f"[Lexicon] New word registered: '{word}' → {symbol}")
        
        return symbol
    
    def _assign_symbol(self, word: str) -> str:
        """
        Assign a stable symbol to a word.
        
        Format: WORD_<index>
        Example: "apple" → "WORD_00001"
        
        This is NOT a hash. It's a sequential ID.
        It's permanent. It never changes.
        """
        index = len(self.word_to_symbol) + 1
        symbol = f"WORD_{index:05d}"
        return symbol
    
    def update_frequency(self, word: str):
        """
        Update lifetime frequency for a word.
        
        This is cumulative across ALL documents.
        """
        word = word.lower().strip()
        self.word_frequency[word] += 1
        self.total_words_seen += 1
    
    def update_adjacency(self, word: str, neighbor: str):
        """
        Update lifetime adjacency for a word pair.
        
        Tracks: word appears near neighbor.
        This is cumulative across ALL documents.
        """
        word = word.lower().strip()
        neighbor = neighbor.lower().strip()
        
        if word and neighbor:
            self.word_adjacency[word][neighbor] += 1
    
    def process_document(self, words: List[str], window_size: int = 6):
        """
        Process a complete document.
        
        For each word:
        1. Register word (get stable symbol)
        2. Update frequency
        3. Update adjacency (with neighbors in window)
        
        Args:
            words: List of words in document
            window_size: Context window size (default 6)
        
        Returns:
            List of symbols (one per word)
        """
        symbols = []
        
        for i, word in enumerate(words):
            # Register word and get symbol
            symbol = self.register_word(word)
            symbols.append(symbol)
            
            # Update frequency
            self.update_frequency(word)
            
            # Update adjacency with neighbors
            start = max(0, i - window_size)
            end = min(len(words), i + window_size + 1)
            
            for j in range(start, end):
                if j != i:
                    neighbor = words[j]
                    self.update_adjacency(word, neighbor)
        
        self.total_documents_processed += 1
        
        # Save after each document
        self._save()
        
        return symbols
    
    def get_word_info(self, word: str) -> Dict:
        """
        Get complete information about a word.
        
        Returns:
            Dict with symbol, frequency, adjacencies
        """
        word = word.lower().strip()
        
        if word not in self.word_to_symbol:
            return {"error": f"Word '{word}' not in lexicon"}
        
        return {
            "word": word,
            "symbol": self.word_to_symbol[word],
            "frequency": self.word_frequency[word],
            "adjacencies": dict(self.word_adjacency[word].most_common(10)),
            "total_adjacencies": sum(self.word_adjacency[word].values())
        }
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """
        Get word information from symbol.
        
        Returns:
            Dict with word, frequency, adjacencies
        """
        if symbol not in self.symbol_to_word:
            return {"error": f"Symbol '{symbol}' not in lexicon"}
        
        word = self.symbol_to_word[symbol]
        return self.get_word_info(word)
    
    def get_top_words(self, n: int = 100) -> List[tuple]:
        """
        Get top N most frequent words.
        
        Returns:
            List of (word, frequency) tuples
        """
        return self.word_frequency.most_common(n)
    
    def get_word_neighbors(self, word: str, n: int = 10) -> List[tuple]:
        """
        Get top N neighbors for a word.
        
        Returns:
            List of (neighbor, count) tuples
        """
        word = word.lower().strip()
        
        if word not in self.word_adjacency:
            return []
        
        return self.word_adjacency[word].most_common(n)
    
    def get_statistics(self) -> Dict:
        """
        Get lexicon statistics.
        
        Returns:
            Dict with counts and metrics
        """
        return {
            "unique_words": self.unique_words,
            "total_words_seen": self.total_words_seen,
            "total_documents_processed": self.total_documents_processed,
            "avg_word_frequency": self.total_words_seen / max(1, self.unique_words),
            "lexicon_file": str(self.lexicon_file),
            "lexicon_size_mb": self.lexicon_file.stat().st_size / 1024 / 1024 if self.lexicon_file.exists() else 0
        }
    
    def search_words(self, prefix: str, limit: int = 20) -> List[str]:
        """
        Search for words by prefix.
        
        Args:
            prefix: Word prefix to search
            limit: Max results
        
        Returns:
            List of matching words
        """
        prefix = prefix.lower()
        matches = [w for w in self.word_to_symbol.keys() if w.startswith(prefix)]
        return sorted(matches)[:limit]


if __name__ == "__main__":
    # Test the lexicon
    print("Testing GlobalLexicon...")
    
    lexicon = GlobalLexicon(lexicon_file="data/test_lexicon.jsonl")
    
    # Test document
    doc1 = ["the", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog"]
    doc2 = ["the", "lazy", "cat", "sleeps", "under", "the", "warm", "sun"]
    
    print("\nProcessing document 1...")
    symbols1 = lexicon.process_document(doc1)
    print(f"Symbols: {symbols1}")
    
    print("\nProcessing document 2...")
    symbols2 = lexicon.process_document(doc2)
    print(f"Symbols: {symbols2}")
    
    print("\nLexicon statistics:")
    stats = lexicon.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nTop words:")
    for word, freq in lexicon.get_top_words(10):
        print(f"  {word}: {freq}")
    
    print("\nWord info for 'the':")
    info = lexicon.get_word_info("the")
    print(json.dumps(info, indent=2))
    
    print("\nNeighbors of 'lazy':")
    neighbors = lexicon.get_word_neighbors("lazy")
    for neighbor, count in neighbors:
        print(f"  {neighbor}: {count}")
