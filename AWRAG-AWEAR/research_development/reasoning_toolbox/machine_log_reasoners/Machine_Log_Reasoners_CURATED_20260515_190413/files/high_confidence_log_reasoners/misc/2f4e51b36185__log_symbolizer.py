#!/usr/bin/env python3
"""
Security Log Symbolizer

Adapter layer that converts raw security logs into compact integer-symbol
streams using the Binary Cell Structure engine. Designed for fast
compute-reads on a security workstation.

Engine code is real and functional.
Integration points (log source, output sink, alerting) are pseudocode
marked with PSEUDO: so you can swap in your system's specifics.
"""

import os
import re
import time
import struct
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

# --- Real imports from the engine ---
from binary_cell import BinaryCell, MasterIndex, BinaryCellWriter, BinaryCellReader
from data_integrity import JournalCheckpoint, DataValidator


# ============================================================================
# LOG TOKENIZER — real code
# ============================================================================

class LogTokenizer:
    """
    Breaks raw log lines into normalized tokens suitable for symbolization.
    Handles common security log formats (syslog, JSON, CEF, Windows Event).
    """

    # Regex patterns for structured extraction
    IP_PATTERN = re.compile(r'\b(\d{1,3}\.){3}\d{1,3}\b')
    PORT_PATTERN = re.compile(r':(\d{1,5})\b')
    TIMESTAMP_PATTERN = re.compile(
        r'\d{4}[-/]\d{2}[-/]\d{2}[T ]\d{2}:\d{2}:\d{2}'
    )
    MAC_PATTERN = re.compile(r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}')
    HEX_PATTERN = re.compile(r'0x[0-9A-Fa-f]+')

    # Common security log severity tokens — normalized
    SEVERITY_MAP = {
        'emergency': 'SEV_EMERG', 'alert': 'SEV_ALERT',
        'critical': 'SEV_CRIT', 'crit': 'SEV_CRIT',
        'error': 'SEV_ERROR', 'err': 'SEV_ERROR',
        'warning': 'SEV_WARN', 'warn': 'SEV_WARN',
        'notice': 'SEV_NOTICE', 'info': 'SEV_INFO',
        'debug': 'SEV_DEBUG',
    }

    def tokenize(self, raw_line: str) -> List[str]:
        """
        Tokenize a raw log line into normalized string tokens.

        Returns a list of tokens like:
            ['SEV_WARN', 'sshd', 'failed', 'password', 'IP:192.168.1.50',
             'PORT:22', 'user', 'root', 'attempts', '5']
        """
        tokens = []

        # Strip timestamp — we store it separately, not as symbols
        line = self.TIMESTAMP_PATTERN.sub('', raw_line).strip()

        # Replace structured data with typed placeholders
        for ip in self.IP_PATTERN.findall(line):
            # findall returns the last group; re-extract full match
            pass
        for match in self.IP_PATTERN.finditer(line):
            ip_token = f"IP:{match.group()}"
            line = line.replace(match.group(), '', 1)
            tokens.append(ip_token)

        for match in self.MAC_PATTERN.finditer(line):
            mac_token = f"MAC:{match.group().upper()}"
            line = line.replace(match.group(), '', 1)
            tokens.append(mac_token)

        for match in self.HEX_PATTERN.finditer(line):
            tokens.append(f"HEX:{match.group()}")
            line = line.replace(match.group(), '', 1)

        # Split remaining into words
        words = re.split(r'[\s=\[\]\(\)\{\}:,;|"\']+', line)

        for word in words:
            word = word.strip().lower()
            if not word:
                continue

            # Normalize severity
            if word in self.SEVERITY_MAP:
                tokens.append(self.SEVERITY_MAP[word])
                continue

            # Port numbers
            if word.isdigit() and 1 <= int(word) <= 65535:
                tokens.append(f"PORT:{word}")
                continue

            # Plain token
            tokens.append(word)

        return tokens


# ============================================================================
# SYMBOL TABLE MANAGER — real code wrapping the engine
# ============================================================================

class SymbolTableManager:
    """
    Manages the symbol table lifecycle: build, persist, reload, query.
    Wraps BinaryCellWriter/Reader with security-log-aware logic.
    """

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.data_file = os.path.join(data_dir, 'logsymbols.bin')
        self.index_file = os.path.join(data_dir, 'logsymbols.idx')
        self.journal_file = os.path.join(data_dir, 'logsymbols.journal')

        self.writer: Optional[BinaryCellWriter] = None
        self.reader: Optional[BinaryCellReader] = None
        self.journal: Optional[JournalCheckpoint] = None

        # In-memory fast path: token string -> token_id
        self._cache: Dict[str, int] = {}

        # Context tracking: which tokens appear before/after which
        self._context_window: List[int] = []
        self._window_size = 4  # tokens of context on each side

    def open_for_write(self):
        """Open the symbol table for writing (ingestion mode)."""
        os.makedirs(self.data_dir, exist_ok=True)
        self.writer = BinaryCellWriter(self.data_file, self.index_file)
        self.writer.__enter__()
        self.journal = JournalCheckpoint(self.journal_file)
        self.journal.open()

    def open_for_read(self):
        """Open the symbol table for reading (query mode)."""
        self.reader = BinaryCellReader(self.data_file, self.index_file)
        self.reader.open()
        # Warm the cache from the index
        for word, word_hash in self.reader.index.word_to_hash.items():
            token_id = self.reader.index.hash_to_token_id.get(word_hash)
            if token_id is not None:
                self._cache[word] = token_id

    def close(self):
        """Close all handles."""
        if self.writer:
            self.writer.__exit__(None, None, None)
            self.writer = None
        if self.reader:
            self.reader.close()
            self.reader = None
        if self.journal:
            self.journal.close()
            self.journal = None

    def symbolize_token(self, token: str) -> int:
        """
        Convert a single string token to its integer symbol ID.
        Creates a new symbol if the token hasn't been seen before.

        This is the hot path — cache-first, engine-second.
        """
        # Fast path: in-memory cache
        if token in self._cache:
            return self._cache[token]

        # Slow path: create new symbol via engine
        token_id = self.writer.get_or_create_token_id(token)
        self._cache[token] = token_id
        return token_id

    def flush_cell(self, token: str, token_id: int, frequency: int,
                   before_ctx: List[Tuple[int, int]],
                   after_ctx: List[Tuple[int, int]]):
        """
        Write a fully populated BinaryCell for a token to disk.

        Args:
            token: The string token
            token_id: Its integer symbol ID
            frequency: How many times it appeared
            before_ctx: List of (context_token_id, co_occurrence_count)
            after_ctx: List of (context_token_id, co_occurrence_count)
        """
        cell = BinaryCell(token, token_id, frequency, tone_signature=0)

        for ctx_id, ctx_freq in before_ctx:
            cell.add_before_context(ctx_id, ctx_freq, tone_id=0)
        for ctx_id, ctx_freq in after_ctx:
            cell.add_after_context(ctx_id, ctx_freq, tone_id=0)

        offset = self.writer.write_cell(cell)
        self.journal.add_entry("write", token, token_id, offset)

    def lookup_token(self, token_id: int) -> Optional[str]:
        """Reverse lookup: integer symbol -> original string token."""
        # Check cache first
        for tok, tid in self._cache.items():
            if tid == token_id:
                return tok
        # Fall back to engine index
        if self.reader:
            return self.reader.index.get_word_by_token_id(token_id)
        return None

    def validate(self) -> Tuple[int, list]:
        """Run integrity check on the symbol table."""
        with DataValidator(self.data_file, self.index_file, self.journal_file) as v:
            return v.validate_all()


# ============================================================================
# SYMBOLIZED LOG RECORD — real code
# ============================================================================

class SymbolizedLogRecord:
    """
    A single log line represented as an array of integer symbols
    plus metadata. This is what gets stored/queried instead of raw text.
    """

    # Wire format: timestamp(8) + symbol_count(2) + symbols(4 each) + raw_len(4)
    HEADER_FMT = '>QH'
    SYMBOL_FMT = '>L'

    def __init__(self, timestamp: float, symbols: List[int],
                 raw_length: int = 0, source_tag: int = 0):
        self.timestamp = timestamp
        self.symbols = symbols
        self.raw_length = raw_length
        self.source_tag = source_tag

    def to_bytes(self) -> bytes:
        """Serialize to compact binary for storage."""
        header = struct.pack(self.HEADER_FMT,
                             int(self.timestamp * 1_000_000),  # microsecond epoch
                             len(self.symbols))
        body = b''.join(struct.pack(self.SYMBOL_FMT, s) for s in self.symbols)
        footer = struct.pack('>LH', self.raw_length, self.source_tag)
        return header + body + footer

    @classmethod
    def from_bytes(cls, data: bytes) -> 'SymbolizedLogRecord':
        """Deserialize from binary."""
        ts_us, count = struct.unpack(cls.HEADER_FMT, data[:10])
        symbols = []
        pos = 10
        for _ in range(count):
            sym = struct.unpack(cls.SYMBOL_FMT, data[pos:pos + 4])[0]
            symbols.append(sym)
            pos += 4
        raw_length, source_tag = struct.unpack('>LH', data[pos:pos + 6])
        return cls(ts_us / 1_000_000, symbols, raw_length, source_tag)

    def size_bytes(self) -> int:
        """Size of the serialized record."""
        return 10 + (4 * len(self.symbols)) + 6

    def matches_pattern(self, pattern_symbols: List[int]) -> bool:
        """
        Fast integer-array subsequence match.
        Much faster than regex on raw strings.
        """
        if not pattern_symbols:
            return True
        pi = 0
        for sym in self.symbols:
            if sym == pattern_symbols[pi]:
                pi += 1
                if pi == len(pattern_symbols):
                    return True
        return False


# ============================================================================
# LOG SYMBOLIZER — orchestrator, pseudocode integration points
# ============================================================================

class LogSymbolizer:
    """
    Main orchestrator. Pseudocode sections show where to plug in
    your log source, output sink, and alerting system.
    """

    def __init__(self, data_dir: str):
        self.tokenizer = LogTokenizer()
        self.table = SymbolTableManager(data_dir)

        # Frequency and context accumulators (flushed periodically)
        self._freq: Dict[int, int] = defaultdict(int)
        self._before_ctx: Dict[int, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self._after_ctx: Dict[int, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self._flush_interval = 10_000  # flush every N lines
        self._lines_since_flush = 0

    # ----------------------------------------------------------------
    # INGEST PIPELINE
    # ----------------------------------------------------------------

    def ingest_line(self, raw_line: str, source_tag: int = 0) -> SymbolizedLogRecord:
        """
        Full pipeline: raw log line -> symbolized record.

        PSEUDO: In production, this is called from your log collector:
            # for line in kafka_consumer.poll('security-logs'):
            #     record = symbolizer.ingest_line(line, source_tag=SENSOR_ID)
            #     output_sink.write(record.to_bytes())
        """
        # Step 1: tokenize (real)
        tokens = self.tokenizer.tokenize(raw_line)

        # Step 2: symbolize each token (real)
        symbols = []
        for tok in tokens:
            sym_id = self.table.symbolize_token(tok)
            symbols.append(sym_id)
            self._freq[sym_id] += 1

        # Step 3: track context co-occurrence (real)
        for i, sym in enumerate(symbols):
            for j in range(max(0, i - 4), i):
                self._before_ctx[sym][symbols[j]] += 1
            for j in range(i + 1, min(len(symbols), i + 5)):
                self._after_ctx[sym][symbols[j]] += 1

        # Step 4: build record (real)
        record = SymbolizedLogRecord(
            timestamp=time.time(),
            symbols=symbols,
            raw_length=len(raw_line),
            source_tag=source_tag,
        )

        # Step 5: periodic flush of accumulated context to disk
        self._lines_since_flush += 1
        if self._lines_since_flush >= self._flush_interval:
            self._flush_to_disk()

        return record

    def _flush_to_disk(self):
        """Flush accumulated frequencies and context to the engine."""
        for sym_id, freq in self._freq.items():
            token = self.table.lookup_token(sym_id)
            if token is None:
                continue
            before = list(self._before_ctx[sym_id].items())
            after = list(self._after_ctx[sym_id].items())
            self.table.flush_cell(token, sym_id, freq, before, after)

        self._freq.clear()
        self._before_ctx.clear()
        self._after_ctx.clear()
        self._lines_since_flush = 0

    # ----------------------------------------------------------------
    # QUERY INTERFACE
    # ----------------------------------------------------------------

    def search_logs(self, pattern: str, records: List[SymbolizedLogRecord]) -> List[SymbolizedLogRecord]:
        """
        Search symbolized log records by pattern.
        Converts the search string to symbols, then does integer matching.

        PSEUDO: In production, 'records' comes from your storage backend:
            # records = storage_backend.load_records(
            #     time_range=(start_ts, end_ts),
            #     source_filter=SENSOR_ID
            # )
        """
        # Tokenize + symbolize the search pattern (real)
        pattern_tokens = self.tokenizer.tokenize(pattern)
        pattern_symbols = []
        for tok in pattern_tokens:
            if tok in self.table._cache:
                pattern_symbols.append(self.table._cache[tok])
            else:
                return []  # unknown token = no matches possible

        # Integer subsequence match across all records (real)
        return [r for r in records if r.matches_pattern(pattern_symbols)]

    def decode_record(self, record: SymbolizedLogRecord) -> str:
        """
        Convert a symbolized record back to human-readable text.
        """
        words = []
        for sym in record.symbols:
            word = self.table.lookup_token(sym)
            words.append(word if word else f"<UNK:{sym}>")
        return ' '.join(words)

    def get_cooccurrence(self, token: str) -> Dict[str, int]:
        """
        What tokens commonly appear near this one?
        Useful for anomaly detection — e.g. new neighbors of 'sudo'.

        PSEUDO: Feed this into your anomaly scoring:
            # baseline = load_baseline_cooccurrence('sudo')
            # current  = symbolizer.get_cooccurrence('sudo')
            # anomaly_score = cosine_distance(baseline, current)
            # if anomaly_score > THRESHOLD:
            #     alert_soc_team(token, anomaly_score, current)
        """
        if self.table.reader:
            return self.table.reader.get_context_words(token)
        return {}

    # ----------------------------------------------------------------
    # LIFECYCLE
    # ----------------------------------------------------------------

    def start_ingestion(self):
        """
        Open for writing. Call before processing logs.

        PSEUDO: Called from your service entrypoint:
            # symbolizer = LogSymbolizer('/var/lib/logsym')
            # symbolizer.start_ingestion()
            # for line in log_source:
            #     record = symbolizer.ingest_line(line)
            #     write_to_output_sink(record)
            # symbolizer.stop_ingestion()
        """
        self.table.open_for_write()

    def stop_ingestion(self):
        """Flush remaining data and close."""
        self._flush_to_disk()
        self.table.close()

    def start_query_mode(self):
        """
        Open for reading. Call before searching/decoding.

        PSEUDO: Called from your query API handler:
            # symbolizer = LogSymbolizer('/var/lib/logsym')
            # symbolizer.start_query_mode()
            # results = symbolizer.search_logs(user_query, loaded_records)
            # for r in results:
            #     print(symbolizer.decode_record(r))
            # symbolizer.stop_query_mode()
        """
        self.table.open_for_read()

    def stop_query_mode(self):
        """Close reader."""
        self.table.close()


# ============================================================================
# DEMO — shows the real engine code in action
# ============================================================================

if __name__ == '__main__':
    import tempfile, shutil

    demo_dir = tempfile.mkdtemp(prefix='logsym_')
    print(f"Demo data dir: {demo_dir}\n")

    sym = LogSymbolizer(demo_dir)

    # --- Ingest phase ---
    sym.start_ingestion()

    sample_logs = [
        "2026-04-01T12:00:01 WARN sshd: Failed password for root from 192.168.1.50 port 22",
        "2026-04-01T12:00:02 ERROR sshd: Failed password for admin from 10.0.0.5 port 22",
        "2026-04-01T12:00:03 INFO sshd: Accepted publickey for deploy from 10.0.0.100 port 443",
        "2026-04-01T12:00:04 CRIT kernel: segfault at 0x0000DEAD in /usr/bin/agent",
        "2026-04-01T12:00:05 WARN firewall: DROP TCP 192.168.1.50:44312 -> 10.0.0.5:443 flags=SYN",
    ]

    records = []
    for line in sample_logs:
        rec = sym.ingest_line(line)
        records.append(rec)
        print(f"Symbolized ({len(rec.symbols)} syms, {rec.size_bytes()} bytes) <- {len(line)} char raw")

    sym.stop_ingestion()

    # --- Query phase ---
    sym.start_query_mode()

    print("\n--- Search: 'failed password' ---")
    hits = sym.search_logs("failed password", records)
    for h in hits:
        print(f"  [{h.timestamp:.0f}] {sym.decode_record(h)}")

    print(f"\n--- Co-occurrence for 'sshd' ---")
    ctx = sym.get_cooccurrence('sshd')
    for word, freq in sorted(ctx.items(), key=lambda x: -x[1]):
        print(f"  {word}: {freq}")

    sym.stop_query_mode()

    # Compression ratio
    raw_bytes = sum(len(l.encode()) for l in sample_logs)
    sym_bytes = sum(r.size_bytes() for r in records)
    print(f"\nRaw: {raw_bytes} bytes -> Symbolized: {sym_bytes} bytes "
          f"({sym_bytes/raw_bytes:.1%} of original)")

    # Cleanup
    shutil.rmtree(demo_dir)
    print("\nDone.")
