#!/usr/bin/env python3
"""
Forest AI Multi-Mode Symbol Generator
Supports Regular, Compressed, and Hyper compression modes
with immutable symbol assignments and smart byte allocation
"""

import json
import hashlib
import random
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict
import nltk
from nltk.corpus import words
import os

class ForestAIMultiModeGenerator:
    """Multi-mode symbol generator for Forest AI system"""
    
    def __init__(self, max_words: int = 10000):
        self.max_words = max_words
        self.symbols = {}
        self.word_assignments = {}  # Immutable assignments
        self.popular_4_letter_words = set()
        self.compression_mode = "regular"  # regular, compressed, hyper
        
        # Download NLTK data if needed
        try:
            nltk.data.find('corpora/words')
        except LookupError:
            print("📥 Downloading NLTK words corpus...")
            nltk.download('words', quiet=True)
        
        # Load popular 4-letter words (most common in English)
        self.load_popular_4_letter_words()
        
        print(f"🌲 Initializing Forest AI Multi-Mode Generator (max {max_words} words)...")
    
    def load_popular_4_letter_words(self):
        """Load the most popular 4-letter English words"""
        # Top 100 most common 4-letter words in English
        popular_4_letter = {
            'that', 'with', 'have', 'this', 'will', 'your', 'from', 'they', 'know',
            'want', 'been', 'good', 'much', 'some', 'time', 'very', 'when', 'come',
            'here', 'just', 'like', 'long', 'make', 'many', 'over', 'such', 'take',
            'than', 'them', 'well', 'were', 'what', 'year', 'work', 'back', 'call',
            'came', 'each', 'even', 'find', 'give', 'hand', 'high', 'keep', 'last',
            'left', 'life', 'live', 'look', 'made', 'most', 'move', 'must', 'name',
            'need', 'next', 'open', 'part', 'play', 'said', 'same', 'seem', 'show',
            'side', 'tell', 'turn', 'used', 'want', 'ways', 'week', 'went', 'word',
            'work', 'year', 'also', 'area', 'away', 'book', 'both', 'case', 'come',
            'down', 'each', 'fact', 'feel', 'form', 'full', 'game', 'give', 'help',
            'home', 'idea', 'into', 'kind', 'line', 'look', 'made', 'mind', 'more',
            'move', 'near', 'only', 'over', 'part', 'real', 'room', 'seen', 'side',
            'take', 'tell', 'turn', 'used', 'very', 'want', 'water', 'week', 'well',
            'went', 'what', 'when', 'will', 'word', 'work', 'year'
        }
        
        # Remove duplicates and ensure exactly 4 letters
        self.popular_4_letter_words = {word for word in popular_4_letter if len(word) == 4}
        print(f"📚 Loaded {len(self.popular_4_letter_words)} popular 4-letter words")
    
    def get_symbol_size(self, word: str) -> int:
        """Determine symbol size based on word characteristics"""
        word_len = len(word)
        
        # 1-3 letters: no symbol (plain text)
        if word_len <= 3:
            return 0
        
        # 4 letters: 3 bytes for popular, 4 bytes for uncommon
        if word_len == 4:
            return 3 if word.lower() in self.popular_4_letter_words else 4
        
        # 5+ letters: 4 bytes
        return 4
    
    def generate_symbol_bytes(self, word: str, slot_id: int, symbol_size: int) -> List[int]:
        """Generate symbol bytes for a word"""
        if symbol_size == 0:
            return []
        
        # Create deterministic but unique symbol
        seed_string = f"{word}_{slot_id}_{symbol_size}"
        hash_obj = hashlib.sha256(seed_string.encode())
        hash_bytes = hash_obj.digest()
        
        # Take first N bytes based on symbol size
        return list(hash_bytes[:symbol_size])
    
    def create_visual_grid(self, symbol_bytes: List[int], size: int = 8) -> List[List[int]]:
        """Create visual grid from symbol bytes"""
        if not symbol_bytes:
            return []
        
        grid = [[0 for _ in range(size)] for _ in range(size)]
        
        # Use symbol bytes to determine grid pattern
        byte_sum = sum(symbol_bytes)
        random.seed(byte_sum)
        
        # Fill grid based on symbol bytes
        for i in range(size):
            for j in range(size):
                # Use combination of position and symbol bytes
                cell_value = (symbol_bytes[i % len(symbol_bytes)] + 
                             symbol_bytes[j % len(symbol_bytes)] + 
                             i * j) % 256
                grid[i][j] = 1 if cell_value > 127 else 0
        
        return grid
    
    def grid_to_ascii(self, grid: List[List[int]]) -> str:
        """Convert grid to ASCII art"""
        if not grid:
            return ""
        return '\n'.join(''.join('█' if cell else '░' for cell in row) for row in grid)
    
    def create_word_symbol(self, word: str, slot_id: int) -> Optional[Dict]:
        """Create symbol for a single word"""
        symbol_size = self.get_symbol_size(word)
        
        # 1-3 letter words don't get symbols
        if symbol_size == 0:
            return None
        
        symbol_bytes = self.generate_symbol_bytes(word, slot_id, symbol_size)
        visual_grid = self.create_visual_grid(symbol_bytes)
        
        return {
            "word": word,
            "slot_id": slot_id,
            "symbol_bytes": symbol_bytes,
            "symbol_hex": ''.join(f'{b:02X}' for b in symbol_bytes),
            "symbol_size": symbol_size,
            "visual_grid": visual_grid,
            "visual_ascii": self.grid_to_ascii(visual_grid),
            "compression_mode": "regular"
        }
    
    def create_tree_symbol(self, words: List[str], tree_id: int) -> Dict:
        """Create symbol for a 6-1-6 tree structure"""
        # Tree symbol is 5-8 bytes representing entire semantic structure
        tree_size = min(8, max(5, len(words) // 2))  # Dynamic size based on tree complexity
        
        # Create seed from all words in tree
        seed_string = f"tree_{'_'.join(sorted(words))}_{tree_id}"
        hash_obj = hashlib.sha256(seed_string.encode())
        hash_bytes = hash_obj.digest()
        
        symbol_bytes = list(hash_bytes[:tree_size])
        visual_grid = self.create_visual_grid(symbol_bytes, size=10)  # Larger grid for trees
        
        return {
            "tree_id": tree_id,
            "words": words,
            "anchor_word": words[len(words)//2] if words else "",  # Middle word as anchor
            "symbol_bytes": symbol_bytes,
            "symbol_hex": ''.join(f'{b:02X}' for b in symbol_bytes),
            "symbol_size": tree_size,
            "visual_grid": visual_grid,
            "visual_ascii": self.grid_to_ascii(visual_grid),
            "compression_mode": "compressed"
        }
    
    def create_forest_block_symbol(self, text_block: str, block_id: int) -> Dict:
        """Create symbol for entire forest block (paragraph/thought sequence)"""
        # Forest block symbol is variable length based on semantic complexity
        words = text_block.split()
        complexity = min(12, max(6, len(words) // 10))  # 6-12 bytes based on content
        
        # Create seed from entire text block
        seed_string = f"forest_{hashlib.md5(text_block.encode()).hexdigest()}_{block_id}"
        hash_obj = hashlib.sha256(seed_string.encode())
        hash_bytes = hash_obj.digest()
        
        symbol_bytes = list(hash_bytes[:complexity])
        visual_grid = self.create_visual_grid(symbol_bytes, size=12)  # Large grid for forest blocks
        
        return {
            "block_id": block_id,
            "text_preview": text_block[:100] + "..." if len(text_block) > 100 else text_block,
            "word_count": len(words),
            "symbol_bytes": symbol_bytes,
            "symbol_hex": ''.join(f'{b:02X}' for b in symbol_bytes),
            "symbol_size": complexity,
            "visual_grid": visual_grid,
            "visual_ascii": self.grid_to_ascii(visual_grid),
            "compression_mode": "hyper"
        }
    
    def load_base_words(self) -> List[str]:
        """Load base English words from NLTK"""
        print("📚 Loading common English words...")
        
        try:
            word_list = words.words()
            # Filter to common English words (no proper nouns, reasonable length)
            filtered_words = [
                word.lower() for word in word_list 
                if word.islower() and 2 <= len(word) <= 15 and word.isalpha()
            ]
            
            # Take most common subset
            common_words = sorted(set(filtered_words))[:self.max_words]
            print(f"✅ Loaded {len(common_words)} base words")
            return common_words
            
        except Exception as e:
            print(f"❌ Error loading words: {e}")
            # Fallback to basic word list
            return ['computer', 'system', 'process', 'network', 'algorithm', 'data']
    
    def expand_words(self, base_words: List[str]) -> List[str]:
        """Expand base words with common variations"""
        print("🔄 Smart word expansion...")
        
        expanded = set(base_words)
        
        for word in base_words:
            # Add common suffixes
            variations = [
                word + 's',      # plural
                word + 'ed',     # past tense
                word + 'ing',    # present participle
                word + 'er',     # comparative/agent
                word + 'est',    # superlative
                word + 'ly',     # adverb
                word + 'tion',   # noun form
                word + 'able',   # adjective
                word + 'ful',    # adjective
                word + 'less',   # adjective
            ]
            
            # Add valid variations
            for variation in variations:
                if len(variation) <= 15:  # Reasonable length limit
                    expanded.add(variation)
        
        result = sorted(list(expanded))
        print(f"✅ Expanded to {len(result)} total words")
        return result
    
    def assign_words_to_slots(self, words: List[str]) -> Dict[str, List[str]]:
        """Assign words to A-Z slots based on first letter"""
        print("🎯 Assigning words to slots...")
        
        slots = defaultdict(list)
        
        for word in words:
            first_letter = word[0].upper() if word and word[0].isalpha() else 'A'
            slots[first_letter].append(word)
        
        # Ensure all A-Z slots exist
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            if letter not in slots:
                slots[letter] = []
        
        print(f"✅ Assigned {len(words)} words to slots")
        return dict(slots)
    
    def generate_all_symbols(self, mode: str = "regular"):
        """Generate symbols for all words in specified mode"""
        self.compression_mode = mode
        print(f"🧬 Generating symbols in {mode.upper()} mode...")
        
        # Load and expand words
        base_words = self.load_base_words()
        all_words = self.expand_words(base_words)
        word_slots = self.assign_words_to_slots(all_words)
        
        self.symbols = {}
        slot_counter = 0
        
        if mode == "regular":
            # Regular mode: individual word symbols
            for slot_id, words_in_slot in word_slots.items():
                for word in words_in_slot:
                    symbol = self.create_word_symbol(word, slot_counter)
                    if symbol:  # Only store if word gets a symbol
                        self.symbols[word] = symbol
                        self.word_assignments[word] = symbol  # Immutable assignment
                    slot_counter += 1
        
        elif mode == "compressed":
            # Compressed mode: tree-level symbols (6-1-6 structures)
            tree_counter = 0
            for slot_id, words_in_slot in word_slots.items():
                # Group words into 6-1-6 trees
                for i in range(0, len(words_in_slot), 13):  # 6+1+6 = 13 words per tree
                    tree_words = words_in_slot[i:i+13]
                    if len(tree_words) >= 3:  # Minimum viable tree
                        tree_symbol = self.create_tree_symbol(tree_words, tree_counter)
                        tree_key = f"tree_{tree_counter}"
                        self.symbols[tree_key] = tree_symbol
                        tree_counter += 1
        
        elif mode == "hyper":
            # Hyper mode: forest block symbols (paragraph-level)
            # Simulate paragraph blocks from word groups
            block_counter = 0
            for slot_id, words_in_slot in word_slots.items():
                # Group words into paragraph-like blocks
                for i in range(0, len(words_in_slot), 50):  # ~50 words per block
                    block_words = words_in_slot[i:i+50]
                    if len(block_words) >= 10:  # Minimum viable block
                        text_block = ' '.join(block_words)
                        forest_symbol = self.create_forest_block_symbol(text_block, block_counter)
                        block_key = f"forest_block_{block_counter}"
                        self.symbols[block_key] = forest_symbol
                        block_counter += 1
        
        print(f"✅ Generated {len(self.symbols)} symbols in {mode.upper()} mode")
        return self.symbols
    
    def get_word_symbol(self, word: str) -> Optional[Dict]:
        """Get symbol for a specific word (immutable lookup)"""
        # Check immutable assignments first
        if word in self.word_assignments:
            return self.word_assignments[word]
        
        # Check current symbols
        return self.symbols.get(word)
    
    def export_symbols(self, filename: str):
        """Export symbols to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.symbols, f, indent=2)
        print(f"📤 Exported {len(self.symbols)} symbols to {filename}")
    
    def get_compression_stats(self) -> Dict:
        """Get compression statistics for current mode"""
        stats = {
            "mode": self.compression_mode,
            "total_symbols": len(self.symbols),
            "symbol_sizes": defaultdict(int),
            "total_bytes": 0
        }
        
        for symbol_data in self.symbols.values():
            size = symbol_data.get("symbol_size", 0)
            stats["symbol_sizes"][size] += 1
            stats["total_bytes"] += size
        
        return stats

def main():
    """Demo the multi-mode symbol generator"""
    print("🔥💥 FOREST AI MULTI-MODE SYMBOL GENERATOR")
    print("=" * 60)
    
    generator = ForestAIMultiModeGenerator(max_words=1000)  # Smaller for demo
    
    # Test all three modes
    modes = ["regular", "compressed", "hyper"]
    
    for mode in modes:
        print(f"\n🧪 TESTING {mode.upper()} MODE:")
        print("-" * 40)
        
        symbols = generator.generate_all_symbols(mode)
        stats = generator.get_compression_stats()
        
        print(f"📊 Mode: {stats['mode'].upper()}")
        print(f"   Total symbols: {stats['total_symbols']}")
        print(f"   Total bytes: {stats['total_bytes']}")
        print(f"   Symbol sizes: {dict(stats['symbol_sizes'])}")
        
        # Export symbols for this mode
        filename = f"forest_ai_symbols_{mode}.json"
        generator.export_symbols(filename)
        
        # Show sample symbols
        print(f"🔍 Sample symbols:")
        sample_count = 0
        for key, symbol in symbols.items():
            if sample_count >= 3:
                break
            hex_val = symbol.get('symbol_hex', 'N/A')
            size = symbol.get('symbol_size', 0)
            print(f"   {key[:20]:20} → {hex_val} ({size} bytes)")
            sample_count += 1
    
    print("\n" + "=" * 60)
    print("✅ MULTI-MODE TESTING COMPLETE!")
    print("🌲 Ready for HTML interface integration!")

if __name__ == "__main__":
    main()

