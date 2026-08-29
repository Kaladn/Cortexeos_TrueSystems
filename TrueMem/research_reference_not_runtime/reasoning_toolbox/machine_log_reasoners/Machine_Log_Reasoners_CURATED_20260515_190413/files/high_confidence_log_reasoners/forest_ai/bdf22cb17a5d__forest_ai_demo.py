#!/usr/bin/env python3
"""
Forest AI - Complete System Demo
Demonstrates the full Forest AI Symbol Generation and Lexicon Bridge system
"""

from forest_lexicon_bridge import ForestLexiconBridge
import json

def main():
    """Demo the complete Forest AI system"""
    print("🔥💥 FOREST AI - COMPLETE SYSTEM DEMO")
    print("=" * 60)
    
    # Initialize the bridge (this loads existing slots)
    print("🌉 Initializing Forest AI Lexicon Bridge...")
    bridge = ForestLexiconBridge()
    
    # Get system statistics
    stats = bridge.get_slot_statistics()
    print(f"\n📊 SYSTEM STATISTICS:")
    print(f"   Total slots: {stats['total_slots']}")
    print(f"   Total words: {stats['total_words']}")
    print(f"   Total symbols: {stats['total_symbols']}")
    
    # Show top 5 slots by word count
    print(f"\n🏆 TOP 5 SLOTS BY WORD COUNT:")
    sorted_slots = sorted(stats['slot_details'].items(), 
                         key=lambda x: x[1]['word_count'], reverse=True)
    for i, (slot_id, details) in enumerate(sorted_slots[:5]):
        print(f"   {i+1}. Slot {slot_id}: {details['word_count']} words")
    
    # Demonstrate word search
    print(f"\n🔍 WORD SEARCH DEMONSTRATION:")
    test_words = ['computer', 'algorithm', 'system', 'process', 'network', 
                  'programming', 'development', 'technology', 'artificial', 'intelligence']
    
    for word in test_words:
        result = bridge.search_word_in_slots(word)
        if result:
            symbol = result['symbol']
            print(f"   {word:12} → Slot {result['slot_id']} → {symbol['symbol_hex']} → {symbol['visual_ascii'].split()[0]}")
        else:
            print(f"   {word:12} → Not found")
    
    # Show detailed symbol for one word
    print(f"\n🧬 DETAILED SYMBOL EXAMPLE:")
    result = bridge.search_word_in_slots('computer')
    if result and result['symbol']:
        symbol = result['symbol']
        print(f"   Word: {symbol['word']}")
        print(f"   Slot: {result['slot_id']}")
        print(f"   Hex: {symbol['symbol_hex']}")
        print(f"   Bytes: {symbol['symbol_bytes']}")
        print(f"   Visual Grid:")
        for line in symbol['visual_ascii'].split('\n'):
            print(f"     {line}")
    
    # Demonstrate slot contents
    print(f"\n📁 SLOT CONTENTS SAMPLE (Slot A - first 10 words):")
    slot_a_contents = bridge.get_slot_contents('A')
    if slot_a_contents and 'word_slots' in slot_a_contents:
        words = slot_a_contents['word_slots'][:10]
        for word in words:
            symbol = slot_a_contents['symbol'].get(word, {})
            hex_val = symbol.get('symbol_hex', 'N/A')
            print(f"   {word:15} → {hex_val}")
    
    # Show system capabilities
    print(f"\n⚡ SYSTEM CAPABILITIES:")
    print(f"   ✅ Symbol Generation: 4-byte unique symbols per word")
    print(f"   ✅ Visual Representation: 8x8 grid patterns")
    print(f"   ✅ Slot Management: A-Z alphabetical organization")
    print(f"   ✅ Word Search: Fast lookup across all slots")
    print(f"   ✅ Backup System: Automatic slot file backups")
    print(f"   ✅ Export Capability: JSON export of all symbols")
    print(f"   ✅ Batch Processing: Efficient bulk operations")
    print(f"   ✅ Extensible: Ready for MIDI tones and binary patterns")
    
    # Performance metrics
    print(f"\n🚀 PERFORMANCE METRICS:")
    print(f"   Words processed: {stats['total_words']:,}")
    print(f"   Symbols generated: {stats['total_symbols']:,}")
    print(f"   Average words per slot: {stats['total_words'] // stats['total_slots']:,}")
    print(f"   Storage efficiency: 4 bytes per symbol + metadata")
    
    print("=" * 60)
    print("✅ FOREST AI SYSTEM DEMO COMPLETE!")
    print("🌲 Ready for integration with Forest Tokenizer!")

if __name__ == "__main__":
    main()

