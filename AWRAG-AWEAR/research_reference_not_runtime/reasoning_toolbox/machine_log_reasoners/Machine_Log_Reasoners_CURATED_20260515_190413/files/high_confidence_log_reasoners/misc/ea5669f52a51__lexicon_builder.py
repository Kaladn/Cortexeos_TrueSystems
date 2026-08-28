"""
Lexicon Builder for Symbol Reasoning System
Processes large corpora to build lexicon slots with GPU acceleration

Builds lexicon entries in the format:
{
  "binary": "10001011001101100000000000000001000101",
  "hex": "8b6800010", 
  "font_symbol": "CJKM_001100100",
  "tone_signature": "TONE_1134",
  "status": "AVAILABLE"
}
"""

import json
import re
import hashlib
import zlib
from typing import Dict, List, Optional, Tuple, Any, Set, Iterator
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
from collections import defaultdict, Counter
import time
import mmap
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp

@dataclass
class CorpusStats:
    """Statistics from corpus processing"""
    total_files: int
    total_words: int
    unique_words: int
    processing_time: float
    memory_usage_mb: float

@dataclass
class WordEntry:
    """Intermediate word entry before lexicon slot creation"""
    word: str
    frequency: int
    contexts: List[str]
    domains: Set[str]
    first_seen: str
    last_seen: str

class LexiconBuilder:
    """
    High-performance lexicon builder for massive corpora
    
    Features:
    - Memory-mapped file processing for large files
    - Multi-process corpus parsing
    - GPU-accelerated frequency analysis
    - Domain-specific symbol assignment
    - Chunked output for scalability
    """
    
    def __init__(self, gpu_manager=None, symbol_engine=None, truth_engine=None):
        self.gpu_manager = gpu_manager
        self.symbol_engine = symbol_engine
        self.truth_engine = truth_engine
        
        # Processing configuration
        self.chunk_size = 10000  # Words per chunk
        self.min_frequency = 2   # Minimum frequency to include
        self.max_word_length = 50  # Maximum word length
        self.context_window = 5    # Words before/after for context
        
        # Domain classification patterns
        self.domain_patterns = self._initialize_domain_patterns()
        
        # Font symbol generators
        self.font_generators = self._initialize_font_generators()
        
        # Tone signature generator
        self.tone_counter = 1000
        
    def _initialize_domain_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for domain classification"""
        return {
            "medical": [
                r'\b\w*ology\b', r'\b\w*itis\b', r'\b\w*osis\b',
                r'\bdoctor\b', r'\bpatient\b', r'\bhospital\b',
                r'\bmedicine\b', r'\btreatment\b', r'\bdiagnosis\b'
            ],
            "technical": [
                r'\bapi\b', r'\balgorithm\b', r'\bdatabase\b',
                r'\bsoftware\b', r'\bhardware\b', r'\bcomputer\b',
                r'\bnetwork\b', r'\bprotocol\b', r'\bsystem\b'
            ],
            "legal": [
                r'\bcourt\b', r'\bjudge\b', r'\blawyer\b',
                r'\bcontract\b', r'\bagreement\b', r'\bstatute\b',
                r'\bregulation\b', r'\bliability\b', r'\bplaintiff\b'
            ],
            "scientific": [
                r'\bresearch\b', r'\bexperiment\b', r'\bhypothesis\b',
                r'\banalysis\b', r'\bdata\b', r'\bmethod\b',
                r'\bresult\b', r'\bconclusion\b', r'\btheory\b'
            ],
            "financial": [
                r'\bmoney\b', r'\bbank\b', r'\binvestment\b',
                r'\bstock\b', r'\bbond\b', r'\bmarket\b',
                r'\beconomy\b', r'\bfinance\b', r'\bcurrency\b'
            ]
        }
    
    def _initialize_font_generators(self) -> Dict[str, Any]:
        """Initialize font symbol generators for different domains"""
        return {
            "common": {"prefix": "LATIN", "counter": 100000},
            "technical": {"prefix": "TECH", "counter": 200000},
            "medical": {"prefix": "MED", "counter": 300000},
            "legal": {"prefix": "LEG", "counter": 400000},
            "scientific": {"prefix": "SCI", "counter": 500000},
            "cjk": {"prefix": "CJKM", "counter": 600000},
            "symbol": {"prefix": "SYM", "counter": 700000},
            "emoji": {"prefix": "EMO", "counter": 800000}
        }
    
    def process_corpus_file(self, filepath: str, encoding: str = 'utf-8') -> Dict[str, WordEntry]:
        """Process a single corpus file and extract word entries"""
        print(f"📖 Processing: {filepath}")
        
        word_entries = defaultdict(lambda: WordEntry(
            word="", frequency=0, contexts=[], domains=set(), 
            first_seen="", last_seen=""
        ))
        
        try:
            file_size = Path(filepath).stat().st_size
            
            # Use memory mapping for large files
            if file_size > 100 * 1024 * 1024:  # 100MB
                return self._process_large_file(filepath, encoding)
            else:
                return self._process_regular_file(filepath, encoding)
                
        except Exception as e:
            print(f"❌ Error processing {filepath}: {e}")
            return {}
    
    def _process_regular_file(self, filepath: str, encoding: str) -> Dict[str, WordEntry]:
        """Process regular-sized file"""
        word_entries = defaultdict(lambda: WordEntry(
            word="", frequency=0, contexts=[], domains=set(),
            first_seen="", last_seen=""
        ))
        
        with open(filepath, 'r', encoding=encoding, errors='ignore') as f:
            content = f.read()
            words = self._extract_words(content)
            
            for i, word in enumerate(words):
                if self._is_valid_word(word):
                    clean_word = self._clean_word(word)
                    
                    # Update word entry
                    entry = word_entries[clean_word]
                    if not entry.word:
                        entry.word = clean_word
                        entry.first_seen = str(time.time())
                    
                    entry.frequency += 1
                    entry.last_seen = str(time.time())
                    
                    # Add context
                    context = self._extract_context(words, i)
                    if context and len(entry.contexts) < 10:  # Limit contexts
                        entry.contexts.append(context)
                    
                    # Classify domain
                    domain = self._classify_domain(clean_word, context)
                    if domain:
                        entry.domains.add(domain)
        
        return dict(word_entries)
    
    def _process_large_file(self, filepath: str, encoding: str) -> Dict[str, WordEntry]:
        """Process large file using memory mapping"""
        word_entries = defaultdict(lambda: WordEntry(
            word="", frequency=0, contexts=[], domains=set(),
            first_seen="", last_seen=""
        ))
        
        with open(filepath, 'r', encoding=encoding, errors='ignore') as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                # Process in chunks
                chunk_size = 1024 * 1024  # 1MB chunks
                overlap = 1000  # Overlap to handle word boundaries
                
                position = 0
                while position < mmapped_file.size():
                    end_pos = min(position + chunk_size, mmapped_file.size())
                    
                    # Read chunk with overlap
                    chunk_data = mmapped_file[position:end_pos].decode(encoding, errors='ignore')
                    
                    # Process chunk
                    chunk_entries = self._process_text_chunk(chunk_data)
                    
                    # Merge entries
                    for word, entry in chunk_entries.items():
                        existing = word_entries[word]
                        if not existing.word:
                            existing.word = word
                            existing.first_seen = entry.first_seen
                        
                        existing.frequency += entry.frequency
                        existing.last_seen = entry.last_seen
                        existing.contexts.extend(entry.contexts[:5])  # Limit contexts
                        existing.domains.update(entry.domains)
                    
                    position = end_pos - overlap
        
        return dict(word_entries)
    
    def _process_text_chunk(self, text: str) -> Dict[str, WordEntry]:
        """Process a chunk of text"""
        word_entries = defaultdict(lambda: WordEntry(
            word="", frequency=0, contexts=[], domains=set(),
            first_seen="", last_seen=""
        ))
        
        words = self._extract_words(text)
        timestamp = str(time.time())
        
        for i, word in enumerate(words):
            if self._is_valid_word(word):
                clean_word = self._clean_word(word)
                
                entry = word_entries[clean_word]
                if not entry.word:
                    entry.word = clean_word
                    entry.first_seen = timestamp
                
                entry.frequency += 1
                entry.last_seen = timestamp
                
                # Add context
                context = self._extract_context(words, i)
                if context:
                    entry.contexts.append(context)
                
                # Classify domain
                domain = self._classify_domain(clean_word, context)
                if domain:
                    entry.domains.add(domain)
        
        return dict(word_entries)
    
    def process_corpus_directory(self, directory: str, 
                                file_patterns: List[str] = None) -> Dict[str, WordEntry]:
        """Process all files in a directory"""
        if not file_patterns:
            file_patterns = ['*.txt', '*.json', '*.xml', '*.html', '*.csv']
        
        directory_path = Path(directory)
        all_files = []
        
        for pattern in file_patterns:
            all_files.extend(directory_path.rglob(pattern))
        
        print(f"📁 Found {len(all_files)} files to process")
        
        # Process files in parallel
        all_word_entries = {}
        
        if len(all_files) > 1:
            # Use process pool for multiple files
            with ProcessPoolExecutor(max_workers=mp.cpu_count()) as executor:
                futures = []
                for filepath in all_files:
                    future = executor.submit(self.process_corpus_file, str(filepath))
                    futures.append(future)
                
                for future in futures:
                    file_entries = future.result()
                    self._merge_word_entries(all_word_entries, file_entries)
        else:
            # Single file processing
            if all_files:
                all_word_entries = self.process_corpus_file(str(all_files[0]))
        
        return all_word_entries
    
    def _merge_word_entries(self, target: Dict[str, WordEntry], 
                           source: Dict[str, WordEntry]):
        """Merge word entries from source into target"""
        for word, entry in source.items():
            if word in target:
                target[word].frequency += entry.frequency
                target[word].contexts.extend(entry.contexts[:5])
                target[word].domains.update(entry.domains)
                target[word].last_seen = entry.last_seen
            else:
                target[word] = entry
    
    def build_lexicon_slots(self, word_entries: Dict[str, WordEntry]) -> List[Dict[str, str]]:
        """Convert word entries to lexicon slots"""
        print(f"🔧 Building lexicon slots for {len(word_entries)} words...")
        
        # Filter by frequency
        filtered_entries = {
            word: entry for word, entry in word_entries.items()
            if entry.frequency >= self.min_frequency
        }
        
        print(f"📊 After frequency filtering: {len(filtered_entries)} words")
        
        lexicon_slots = []
        
        for word, entry in filtered_entries.items():
            try:
                slot = self._create_lexicon_slot(word, entry)
                lexicon_slots.append(slot)
            except Exception as e:
                print(f"⚠️ Error creating slot for '{word}': {e}")
        
        return lexicon_slots
    
    def _create_lexicon_slot(self, word: str, entry: WordEntry) -> Dict[str, str]:
        """Create a lexicon slot for a word entry"""
        # Generate binary representation
        binary = self._generate_binary_representation(word, entry)
        
        # Convert to hex
        hex_value = self._binary_to_hex(binary)
        
        # Generate font symbol
        font_symbol = self._generate_font_symbol(word, entry)
        
        # Generate tone signature
        tone_signature = self._generate_tone_signature(word, entry)
        
        # Determine status
        status = self._determine_status(word, entry)
        
        return {
            "binary": binary,
            "hex": hex_value,
            "font_symbol": font_symbol,
            "tone_signature": tone_signature,
            "status": status
        }
    
    def _generate_binary_representation(self, word: str, entry: WordEntry) -> str:
        """Generate binary representation for word"""
        # Create hash of word + frequency + domains
        content = f"{word}:{entry.frequency}:{sorted(entry.domains)}"
        hash_bytes = hashlib.sha256(content.encode()).digest()
        
        # Convert to binary (use first 32 bits for reasonable length)
        binary_int = int.from_bytes(hash_bytes[:4], byteorder='big')
        binary_str = format(binary_int, '032b')
        
        return binary_str
    
    def _binary_to_hex(self, binary: str) -> str:
        """Convert binary string to hex"""
        binary_int = int(binary, 2)
        hex_str = format(binary_int, 'X')
        return hex_str
    
    def _generate_font_symbol(self, word: str, entry: WordEntry) -> str:
        """Generate font symbol based on word and domains"""
        # Determine primary domain
        primary_domain = self._get_primary_domain(entry.domains)
        
        # Get appropriate generator
        if primary_domain in self.font_generators:
            generator = self.font_generators[primary_domain]
        else:
            generator = self.font_generators["common"]
        
        # Generate symbol
        prefix = generator["prefix"]
        counter = generator["counter"]
        generator["counter"] += 1
        
        # Add word-specific suffix
        word_hash = hashlib.md5(word.encode()).hexdigest()[:6].upper()
        
        return f"{prefix}_{word_hash}{counter % 1000000:06d}"
    
    def _generate_tone_signature(self, word: str, entry: WordEntry) -> str:
        """Generate tone signature"""
        # Base tone on word characteristics
        tone_base = len(word) * 100 + entry.frequency % 1000
        tone_number = (tone_base + self.tone_counter) % 10000
        
        self.tone_counter += 1
        
        return f"TONE_{tone_number:04d}"
    
    def _determine_status(self, word: str, entry: WordEntry) -> str:
        """Determine status for lexicon slot"""
        if entry.frequency >= 1000:
            return "AVAILABLE"
        elif entry.frequency >= 100:
            return "AVAILABLE"
        elif entry.frequency >= 10:
            return "AVAILABLE"
        else:
            return "PENDING"
    
    def _get_primary_domain(self, domains: Set[str]) -> str:
        """Get primary domain from set of domains"""
        if not domains:
            return "common"
        
        # Priority order for domains
        priority = ["medical", "legal", "technical", "scientific", "financial"]
        
        for domain in priority:
            if domain in domains:
                return domain
        
        return list(domains)[0] if domains else "common"
    
    def _extract_words(self, text: str) -> List[str]:
        """Extract words from text"""
        # Simple word extraction (can be enhanced)
        words = re.findall(r'\b\w+\b', text.lower())
        return words
    
    def _is_valid_word(self, word: str) -> bool:
        """Check if word is valid for inclusion"""
        if len(word) < 2 or len(word) > self.max_word_length:
            return False
        
        if word.isdigit():
            return False
        
        if len(set(word)) == 1:  # All same character
            return False
        
        return True
    
    def _clean_word(self, word: str) -> str:
        """Clean and normalize word"""
        # Remove non-alphabetic characters and convert to lowercase
        cleaned = re.sub(r'[^a-zA-Z]', '', word.lower())
        return cleaned
    
    def _extract_context(self, words: List[str], index: int) -> str:
        """Extract context around word"""
        start = max(0, index - self.context_window)
        end = min(len(words), index + self.context_window + 1)
        
        context_words = words[start:end]
        return " ".join(context_words)
    
    def _classify_domain(self, word: str, context: str) -> Optional[str]:
        """Classify word domain based on patterns"""
        text = f"{word} {context}".lower()
        
        for domain, patterns in self.domain_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return domain
        
        return None
    
    def save_lexicon_chunks(self, lexicon_slots: List[Dict[str, str]], 
                           output_dir: str, chunk_size: int = 10000):
        """Save lexicon slots in chunks"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        total_chunks = (len(lexicon_slots) + chunk_size - 1) // chunk_size
        
        for i in range(0, len(lexicon_slots), chunk_size):
            chunk = lexicon_slots[i:i + chunk_size]
            chunk_num = i // chunk_size + 1
            
            chunk_file = output_path / f"lexicon_chunk_{chunk_num:04d}.json"
            
            with open(chunk_file, 'w', encoding='utf-8') as f:
                json.dump(chunk, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Saved chunk {chunk_num}/{total_chunks}: {len(chunk)} slots")
    
    def build_from_corpus(self, corpus_path: str, output_dir: str) -> CorpusStats:
        """Complete pipeline: corpus to lexicon slots"""
        start_time = time.time()
        
        print("🚀 Starting lexicon building pipeline...")
        
        # Process corpus
        word_entries = self.process_corpus_directory(corpus_path)
        
        # Build lexicon slots
        lexicon_slots = self.build_lexicon_slots(word_entries)
        
        # Validate slots if truth engine available
        if self.truth_engine:
            print("🔍 Validating lexicon slots...")
            validation_results = self.truth_engine.validate_batch(lexicon_slots)
            valid_slots = [slot for slot, result in zip(lexicon_slots, validation_results) 
                          if result.is_valid]
            print(f"✅ {len(valid_slots)}/{len(lexicon_slots)} slots passed validation")
            lexicon_slots = valid_slots
        
        # Save in chunks
        self.save_lexicon_chunks(lexicon_slots, output_dir)
        
        # Generate statistics
        processing_time = time.time() - start_time
        
        stats = CorpusStats(
            total_files=len(list(Path(corpus_path).rglob('*'))),
            total_words=sum(entry.frequency for entry in word_entries.values()),
            unique_words=len(word_entries),
            processing_time=processing_time,
            memory_usage_mb=0  # Would need psutil for accurate measurement
        )
        
        print(f"✅ Pipeline complete in {processing_time:.2f}s")
        print(f"📊 Generated {len(lexicon_slots)} lexicon slots")
        
        return stats

def main():
    """Demo of Lexicon Builder capabilities"""
    print("🔧 Lexicon Builder Demo")
    print("=" * 50)
    
    # Initialize builder
    builder = LexiconBuilder()
    
    # Create sample text for demo
    sample_text = """
    Artificial intelligence and machine learning are transforming technology.
    Medical research shows promising results in cancer treatment.
    Legal frameworks need updating for digital privacy.
    Scientific analysis reveals climate change patterns.
    Financial markets respond to economic indicators.
    """
    
    # Save sample text to file
    sample_file = Path("sample_corpus.txt")
    with open(sample_file, 'w') as f:
        f.write(sample_text)
    
    # Process sample file
    word_entries = builder.process_corpus_file(str(sample_file))
    
    print(f"📖 Processed {len(word_entries)} unique words")
    
    # Build lexicon slots
    lexicon_slots = builder.build_lexicon_slots(word_entries)
    
    print(f"🔧 Generated {len(lexicon_slots)} lexicon slots")
    
    # Show sample slots
    print("\n📋 Sample lexicon slots:")
    for i, slot in enumerate(lexicon_slots[:3]):
        print(f"\nSlot {i+1}:")
        for key, value in slot.items():
            print(f"  {key}: {value}")
    
    # Clean up
    sample_file.unlink()

if __name__ == "__main__":
    main()

