"""
Production Lexicon Builder
Real corpus processing with NLTK word expansion and organized slot generation

Features:
- NLTK-based word expansion (plurals, tenses, derivatives)
- Real corpus file input
- Organized output by letter directories
- Production-ready lexicon slots
- No test files or demos
"""

import json
import os
import re
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict, Counter
import nltk
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.tag import pos_tag
from nltk.corpus import stopwords
import argparse

class ProductionLexiconBuilder:
    """
    Production-grade lexicon builder for real corpus processing
    """
    
    def __init__(self):
        self.setup_nltk()
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        self.word_expansions = {}
        self.slot_counter = 1
        self.domain_counters = {
            'common': 100000,
            'technical': 200000,
            'medical': 300000,
            'legal': 400000,
            'scientific': 500000,
            'proper': 600000
        }
        
    def setup_nltk(self):
        """Download required NLTK data"""
        required_data = [
            'punkt', 'averaged_perceptron_tagger', 'wordnet',
            'stopwords', 'omw-1.4'
        ]
        
        for data in required_data:
            try:
                nltk.data.find(f'tokenizers/{data}')
            except LookupError:
                print(f"📦 Downloading NLTK data: {data}")
                nltk.download(data, quiet=True)
    
    def get_corpus_file(self) -> str:
        """Get corpus file from user input"""
        while True:
            corpus_file = input("📖 Enter path to corpus file: ").strip()
            
            if not corpus_file:
                print("❌ Please provide a corpus file path")
                continue
                
            corpus_path = Path(corpus_file)
            
            if not corpus_path.exists():
                print(f"❌ File not found: {corpus_file}")
                continue
                
            if not corpus_path.is_file():
                print(f"❌ Path is not a file: {corpus_file}")
                continue
                
            # Check file size
            size_mb = corpus_path.stat().st_size / (1024 * 1024)
            print(f"📊 Corpus file size: {size_mb:.2f} MB")
            
            return str(corpus_path)
    
    def get_output_directory(self) -> str:
        """Get output directory for spare slots"""
        while True:
            output_dir = input("📁 Enter spare slots directory path: ").strip()
            
            if not output_dir:
                print("❌ Please provide an output directory path")
                continue
            
            output_path = Path(output_dir)
            
            # Create directory if it doesn't exist
            try:
                output_path.mkdir(parents=True, exist_ok=True)
                print(f"✅ Output directory ready: {output_path}")
                return str(output_path)
            except Exception as e:
                print(f"❌ Cannot create directory: {e}")
                continue
    
    def process_corpus(self, corpus_file: str) -> Dict[str, Set[str]]:
        """Process corpus file and extract all word variations"""
        print(f"🔍 Processing corpus: {corpus_file}")
        
        word_variations = defaultdict(set)
        
        try:
            with open(corpus_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            print("📝 Tokenizing text...")
            sentences = sent_tokenize(content)
            
            total_sentences = len(sentences)
            processed = 0
            
            for sentence in sentences:
                # Tokenize and tag words
                words = word_tokenize(sentence.lower())
                tagged_words = pos_tag(words)
                
                for word, pos in tagged_words:
                    if self.is_valid_word(word):
                        # Get base form and all variations
                        base_word = self.get_base_word(word, pos)
                        variations = self.expand_word(base_word, pos)
                        
                        # Store all variations
                        for variation in variations:
                            word_variations[base_word].add(variation)
                
                processed += 1
                if processed % 1000 == 0:
                    progress = (processed / total_sentences) * 100
                    print(f"⏳ Progress: {progress:.1f}% ({processed}/{total_sentences} sentences)")
            
            print(f"✅ Extracted {len(word_variations)} base words with variations")
            return dict(word_variations)
            
        except Exception as e:
            print(f"❌ Error processing corpus: {e}")
            return {}
    
    def is_valid_word(self, word: str) -> bool:
        """Check if word is valid for lexicon"""
        if len(word) < 2 or len(word) > 50:
            return False
        
        if not re.match(r'^[a-zA-Z]+$', word):
            return False
        
        if word in self.stop_words:
            return False
        
        if word.isdigit():
            return False
        
        return True
    
    def get_base_word(self, word: str, pos: str) -> str:
        """Get base form of word using lemmatization"""
        # Convert POS tag to WordNet format
        wordnet_pos = self.get_wordnet_pos(pos)
        
        if wordnet_pos:
            return self.lemmatizer.lemmatize(word, wordnet_pos)
        else:
            return self.lemmatizer.lemmatize(word)
    
    def get_wordnet_pos(self, treebank_tag: str) -> Optional[str]:
        """Convert TreeBank POS tag to WordNet POS tag"""
        if treebank_tag.startswith('J'):
            return wordnet.ADJ
        elif treebank_tag.startswith('V'):
            return wordnet.VERB
        elif treebank_tag.startswith('N'):
            return wordnet.NOUN
        elif treebank_tag.startswith('R'):
            return wordnet.ADV
        else:
            return None
    
    def expand_word(self, base_word: str, pos: str) -> Set[str]:
        """Expand word to all possible variations"""
        variations = {base_word}
        
        # Get WordNet synsets for the word
        synsets = wordnet.synsets(base_word)
        
        for synset in synsets:
            # Add lemmas (different forms)
            for lemma in synset.lemmas():
                lemma_name = lemma.name().replace('_', ' ')
                if self.is_valid_word(lemma_name.replace(' ', '')):
                    variations.add(lemma_name.replace(' ', ''))
        
        # Add morphological variations based on POS
        if pos.startswith('N'):  # Noun
            variations.update(self.get_noun_variations(base_word))
        elif pos.startswith('V'):  # Verb
            variations.update(self.get_verb_variations(base_word))
        elif pos.startswith('J'):  # Adjective
            variations.update(self.get_adjective_variations(base_word))
        
        return variations
    
    def get_noun_variations(self, word: str) -> Set[str]:
        """Get noun variations (plurals, etc.)"""
        variations = set()
        
        # Simple plural rules
        if word.endswith('y') and len(word) > 1 and word[-2] not in 'aeiou':
            variations.add(word[:-1] + 'ies')
        elif word.endswith(('s', 'sh', 'ch', 'x', 'z')):
            variations.add(word + 'es')
        elif word.endswith('f'):
            variations.add(word[:-1] + 'ves')
        elif word.endswith('fe'):
            variations.add(word[:-2] + 'ves')
        else:
            variations.add(word + 's')
        
        return variations
    
    def get_verb_variations(self, word: str) -> Set[str]:
        """Get verb variations (tenses, etc.)"""
        variations = set()
        
        # Present tense (3rd person singular)
        if word.endswith('y') and len(word) > 1 and word[-2] not in 'aeiou':
            variations.add(word[:-1] + 'ies')
        elif word.endswith(('s', 'sh', 'ch', 'x', 'z')):
            variations.add(word + 'es')
        else:
            variations.add(word + 's')
        
        # Past tense and past participle
        if word.endswith('e'):
            variations.add(word + 'd')
        elif word.endswith('y') and len(word) > 1 and word[-2] not in 'aeiou':
            variations.add(word[:-1] + 'ied')
        else:
            variations.add(word + 'ed')
        
        # Present participle
        if word.endswith('e') and not word.endswith('ee'):
            variations.add(word[:-1] + 'ing')
        elif len(word) > 2 and word[-1] not in 'aeiou' and word[-2] in 'aeiou' and word[-3] not in 'aeiou':
            variations.add(word + word[-1] + 'ing')  # Double consonant
        else:
            variations.add(word + 'ing')
        
        return variations
    
    def get_adjective_variations(self, word: str) -> Set[str]:
        """Get adjective variations (comparative, superlative)"""
        variations = set()
        
        # Comparative and superlative
        if len(word) <= 2 or (len(word) == 3 and word[-1] not in 'aeiou'):
            # Short adjectives: add -er, -est
            if word.endswith('e'):
                variations.add(word + 'r')
                variations.add(word + 'st')
            elif word.endswith('y'):
                variations.add(word[:-1] + 'ier')
                variations.add(word[:-1] + 'iest')
            else:
                variations.add(word + 'er')
                variations.add(word + 'est')
        
        return variations
    
    def classify_domain(self, word: str) -> str:
        """Classify word into domain"""
        # Medical terms
        if any(pattern in word for pattern in ['medic', 'clinic', 'therap', 'pharmac', 'bio']):
            return 'medical'
        
        # Technical terms
        if any(pattern in word for pattern in ['tech', 'comput', 'software', 'data', 'algorithm']):
            return 'technical'
        
        # Legal terms
        if any(pattern in word for pattern in ['legal', 'court', 'law', 'contract', 'statute']):
            return 'legal'
        
        # Scientific terms
        if any(pattern in word for pattern in ['scien', 'research', 'experiment', 'analysis']):
            return 'scientific'
        
        # Proper nouns (capitalized in original)
        if word[0].isupper():
            return 'proper'
        
        return 'common'
    
    def create_lexicon_slot(self, word: str, domain: str) -> Dict[str, str]:
        """Create lexicon slot for word"""
        # Generate binary representation
        word_hash = hashlib.sha256(f"{word}:{domain}:{self.slot_counter}".encode()).digest()
        binary_int = int.from_bytes(word_hash[:4], byteorder='big')
        binary = format(binary_int, '032b')
        
        # Convert to hex
        hex_value = format(binary_int, '08X')
        
        # Generate font symbol
        domain_counter = self.domain_counters[domain]
        self.domain_counters[domain] += 1
        
        domain_prefixes = {
            'common': 'LATIN',
            'technical': 'TECH',
            'medical': 'MED',
            'legal': 'LEG',
            'scientific': 'SCI',
            'proper': 'PROP'
        }
        
        prefix = domain_prefixes[domain]
        word_hash_short = hashlib.md5(word.encode()).hexdigest()[:6].upper()
        font_symbol = f"{prefix}_{word_hash_short}{domain_counter % 1000000:06d}"
        
        # Generate tone signature
        tone_number = (len(word) * 100 + self.slot_counter) % 10000
        tone_signature = f"TONE_{tone_number:04d}"
        
        # Determine status
        status = "AVAILABLE"
        
        self.slot_counter += 1
        
        return {
            "binary": binary,
            "hex": hex_value,
            "font_symbol": font_symbol,
            "tone_signature": tone_signature,
            "status": status
        }
    
    def organize_slots_by_letter(self, word_variations: Dict[str, Set[str]], 
                                output_dir: str):
        """Create lexicon slots organized by letter directories"""
        output_path = Path(output_dir)
        
        # Create letter directories
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            letter_dir = output_path / letter
            letter_dir.mkdir(exist_ok=True)
        
        total_words = sum(len(variations) for variations in word_variations.values())
        processed_words = 0
        
        print(f"🔧 Creating lexicon slots for {total_words} word variations...")
        
        for base_word, variations in word_variations.items():
            domain = self.classify_domain(base_word)
            
            for variation in variations:
                if not variation or not variation[0].isalpha():
                    continue
                
                # Create lexicon slot
                slot = self.create_lexicon_slot(variation, domain)
                
                # Determine letter directory
                first_letter = variation[0].upper()
                letter_dir = output_path / first_letter
                
                # Create filename
                safe_word = re.sub(r'[^a-zA-Z0-9]', '_', variation)
                filename = f"{safe_word}_{self.slot_counter:08d}.json"
                slot_file = letter_dir / filename
                
                # Save slot
                with open(slot_file, 'w', encoding='utf-8') as f:
                    json.dump(slot, f, indent=2, ensure_ascii=False)
                
                processed_words += 1
                if processed_words % 1000 == 0:
                    progress = (processed_words / total_words) * 100
                    print(f"💾 Progress: {progress:.1f}% ({processed_words}/{total_words} slots)")
        
        print(f"✅ Created {processed_words} lexicon slots in {output_dir}")
        
        # Generate summary
        self.generate_summary(output_path, processed_words)
    
    def generate_summary(self, output_path: Path, total_slots: int):
        """Generate summary of lexicon generation"""
        summary = {
            "generation_timestamp": time.time(),
            "total_slots": total_slots,
            "domain_counters": self.domain_counters,
            "letter_distribution": {},
            "metadata": {
                "builder_version": "1.0",
                "nltk_version": nltk.__version__,
                "expansion_method": "NLTK WordNet + Morphological Rules"
            }
        }
        
        # Count slots per letter
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            letter_dir = output_path / letter
            if letter_dir.exists():
                slot_count = len(list(letter_dir.glob('*.json')))
                summary["letter_distribution"][letter] = slot_count
        
        # Save summary
        summary_file = output_path / "lexicon_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Summary saved to: {summary_file}")
        
        # Print statistics
        print("\n📈 LEXICON GENERATION COMPLETE")
        print("=" * 50)
        print(f"Total slots created: {total_slots:,}")
        print(f"Domain distribution:")
        for domain, count in self.domain_counters.items():
            if count > 100000:  # Only show domains that were used
                used_count = count - (100000 + list(self.domain_counters.keys()).index(domain) * 100000)
                print(f"  {domain}: {used_count:,}")
        
        print(f"\nTop letter distributions:")
        letter_counts = summary["letter_distribution"]
        sorted_letters = sorted(letter_counts.items(), key=lambda x: x[1], reverse=True)
        for letter, count in sorted_letters[:10]:
            print(f"  {letter}: {count:,} slots")
    
    def run(self):
        """Main execution pipeline"""
        print("🚀 PRODUCTION LEXICON BUILDER")
        print("=" * 50)
        
        # Get inputs
        corpus_file = self.get_corpus_file()
        output_dir = self.get_output_directory()
        
        # Process corpus
        word_variations = self.process_corpus(corpus_file)
        
        if not word_variations:
            print("❌ No words extracted from corpus")
            return
        
        # Generate lexicon slots
        self.organize_slots_by_letter(word_variations, output_dir)
        
        print("\n🎉 LEXICON GENERATION COMPLETE!")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Production Lexicon Builder")
    parser.add_argument("--corpus", help="Path to corpus file")
    parser.add_argument("--output", help="Output directory for spare slots")
    
    args = parser.parse_args()
    
    builder = ProductionLexiconBuilder()
    
    if args.corpus and args.output:
        # Non-interactive mode
        if not Path(args.corpus).exists():
            print(f"❌ Corpus file not found: {args.corpus}")
            return
        
        output_path = Path(args.output)
        output_path.mkdir(parents=True, exist_ok=True)
        
        word_variations = builder.process_corpus(args.corpus)
        builder.organize_slots_by_letter(word_variations, args.output)
    else:
        # Interactive mode
        builder.run()

if __name__ == "__main__":
    main()

