# Code-Derived Help

This help file is derived from the current code in:

```text
src/local_memory_chat/cli.py
src/local_memory_chat/memory.py
```

It describes what the program actually does now.

It does not describe planned features unless the current code already implements them.

## Short Version

Local Memory Chat keeps private runtime memory under a profile folder.

It can:

```text
create runtime folders
import demo chat
add one file to hot memory
attach private sources read-only
index attached text files/folders into hot memory
inspect attached binary files without decoding them
convert SQLite rows into support binaries
ask questions against hot memory
write packets and receipts
```

It does not currently call a model.

It does not currently summarize with an LLM.

It does not currently decode arbitrary chat binaries into turns.

## Runtime Layout

The runtime path is controlled by `--runtime-root`.

The default runtime root is:

```text
runtime
```

Each profile lives at:

```text
runtime/profiles/<profile>/
```

The code creates these profile folders:

```text
sources/
hot/
packets/
receipts/
support/
```

The important files are:

```text
sources/source_manifest.jsonl
sources/attached_sources.jsonl
hot/hot_counts.json
hot/hot_address_index.jsonl
packets/memory_packet_<timestamp>_<question_hash>.json
receipts/*.json
support/sqlite_support_<source_id>.rows.bin
support/sqlite_support_<source_id>.row_index.jsonl
```

## Profiles

Most commands accept:

```text
--profile <name>
```

The profile name becomes part of the runtime path.

Example:

```powershell
python -m local_memory_chat.cli init --profile lee
```

This writes:

```text
runtime/profiles/lee/profile_manifest.json
```

The profile manifest records:

```text
schema
created_at
memory_profile_id
runtime_root
private_runtime=true
```

## What A Source Is

The code uses two related source records.

`source_manifest.jsonl` records sources that have been admitted into hot memory.

`attached_sources.jsonl` records sources that were attached read-only but may or may not have been indexed yet.

Source IDs look like:

```text
SRC-...
```

They are created from SHA-256 hashes.

## What A Memory Item Is

When a source is indexed into hot memory, the code writes address records to:

```text
hot/hot_address_index.jsonl
```

Each address record contains:

```text
memory_id
source_id
chunk_id
tier
source_type
source_label
timestamp
line_start
line_end
char_start
char_end
snippet
citation
anchors
```

Memory IDs look like:

```text
MEM-...
```

Memory citations look like:

```text
MEMCIT-...
```

The citation points to a hot-memory address record.

## Anchors

The code extracts anchors using this regex:

```text
[A-Za-z0-9][A-Za-z0-9_.-]*
```

Then it lowercases with `casefold()`.

Then it strips leading/trailing:

```text
.
_
-
```

Then it removes a small stop list:

```text
a
an
and
about
are
as
at
be
by
did
do
for
from
in
is
it
of
on
or
that
the
to
we
what
```

The code also creates a few simple anchor variants:

```text
plural ending s can add a singular-looking variant
ed ending can add a trimmed variant
er ending can add a trimmed variant
renderer can add render
```

Anchors are kept unique per chunk.

## Hot Counts

Hot counts are written to:

```text
hot/hot_counts.json
```

They contain:

```text
anchors
cohabitation
```

`anchors` counts how often anchors appeared.

`cohabitation` counts nearby anchor relationships.

For each anchor in a chunk, the code counts neighbors at these offsets:

```text
-2
-1
+1
+2
```

The cohabitation key looks like:

```text
center|neighbor|offset
```

Example shape:

```text
packet|citation|+1
```

The current code does not store these hot counts in a custom binary file.

The current code stores them as JSON.

## Command: init

Command:

```powershell
python -m local_memory_chat.cli init --profile demo
```

What it does:

```text
creates runtime folders
writes profile_manifest.json
returns paths as JSON
```

It does not ingest data.

## Command: import-demo

Command:

```powershell
python -m local_memory_chat.cli import-demo --profile demo
```

Default demo path:

```text
data/demo/synthetic_chat.jsonl
```

What it does:

```text
reads JSONL demo records
extracts text and tags
anchorizes text plus tags
writes source_manifest.jsonl
writes hot_address_index.jsonl
writes hot_counts.json
writes an intake receipt
```

Each demo record becomes one hot-memory chunk.

Demo records are marked:

```text
private=false
synthetic=true
```

## Command: add-file

Command:

```powershell
python -m local_memory_chat.cli add-file <path> --profile demo --label <label>
```

What it does:

```text
checks the path exists and is a file
hashes the file before reading
reads it as UTF-8 with replacement for bad characters
splits it into line chunks
extracts anchors from each chunk
writes source_manifest.jsonl
appends hot_address_index.jsonl records
merges anchor/cohabitation counts into hot_counts.json
hashes the file again after reading
writes a file intake receipt
```

The default chunk size is:

```text
12 lines
```

You can change it:

```powershell
python -m local_memory_chat.cli add-file notes.md --profile demo --chunk-lines 20
```

The receipt records whether the source hash stayed unchanged.

## Command: attach-source

Command:

```powershell
python -m local_memory_chat.cli attach-source --profile demo --path <path> --source-type <type> --label <label>
```

Allowed source types:

```text
file
file-root
chat-binary
```

What it does:

```text
checks the path exists
checks the source type matches file/folder expectations
hashes the path
creates a source_id
appends attached_sources.jsonl
writes an attach receipt
```

For `chat-binary`, status is:

```text
attached_not_decoded
```

Attach does not index the source into hot memory.

Attach is a registration step.

## Command: sources

Command:

```powershell
python -m local_memory_chat.cli sources --profile demo
```

What it does:

```text
reads attached_sources.jsonl
reads receipts
merges receipt status into the displayed source list
prints JSON
```

This is why sources can show:

```text
indexed=true
latest_index_status=indexed_hot
latest_inspect_status=not_decoded
sqlite_support_built=true
```

The source manifest itself is append-only.

The displayed truth comes from receipts.

## Command: index-source

Command:

```powershell
python -m local_memory_chat.cli index-source --profile demo --source-id <SRC-id> --hot
```

The `--hot` flag is required.

What it does:

```text
finds the attached source_id
checks the current source hash matches the attached hash
indexes file or file-root sources into hot memory
rejects chat-binary as not decoded
writes an index receipt
```

For `file`:

```text
calls add_file on that file
```

For `file-root`:

```text
walks text-like files under that folder
calls add_file on each one
```

For `chat-binary`:

```text
does not index
writes status attached_not_decoded
```

## File Types Indexed In file-root

`file-root` only indexes these suffixes:

```text
.txt
.md
.markdown
.jsonl
.json
.csv
.log
```

It skips paths with hidden path parts, meaning path parts that start with:

```text
.
```

## Command: inspect-binary

Command:

```powershell
python -m local_memory_chat.cli inspect-binary --profile demo --source-id <SRC-id>
```

Only attached `chat-binary` sources are accepted.

What it does:

```text
finds the attached source
checks it is a file
hashes it
reads a small byte window from the start
guesses obvious file format from first bytes
writes a binary inspect receipt
```

It does not decode messages.

It does not write hot memory.

It does not search inside the binary.

Possible format labels include:

```text
sqlite
gguf
zip
gzip
json_like
plain_text_like
unknown
empty
```

The receipt includes:

```text
size_bytes
sha256
first_bytes_hex
sample_offsets
possible_format
decode_status=not_decoded
no_mutation=true
```

## Command: sqlite-support

Command:

```powershell
python -m local_memory_chat.cli sqlite-support --profile demo --source-id <SRC-id>
```

Only attached `chat-binary` SQLite sources are accepted.

What it does:

```text
opens the SQLite database read-only
reads table names
reads rows from selected tables or all non-sqlite internal tables
writes rows into a runtime support binary
writes a row index JSONL file
writes a SQLite support receipt
```

The support binary path looks like:

```text
support/sqlite_support_<source_id>.rows.bin
```

The row index path looks like:

```text
support/sqlite_support_<source_id>.row_index.jsonl
```

The binary starts with:

```text
LMC-SQLITE-SUPPORT-0
```

Then it writes length-prefixed JSON records.

Each row gets a citation:

```text
SQLCIT-...
```

Each row index record includes:

```text
source_id
table
sqlite_rowid
citation
binary_path
binary_offset
record_length
payload_length
row_hash
```

This lets a checker reopen the support binary, seek to `binary_offset`, read `record_length`, hash the payload, and prove the row record matches the index.

### Live SQLite Sources

If the SQLite file changed since it was attached, this command normally stops with:

```text
source_hash_mismatch
```

You can explicitly allow a live source:

```powershell
python -m local_memory_chat.cli sqlite-support --profile demo --source-id <SRC-id> --allow-live-source
```

When this is used, the receipt records:

```text
attached_hash_matches_before=false
live_source_allowed=true
```

That means the original attach hash was stale, but the support snapshot still records its own before/after hash.

## Command: ask

Command:

```powershell
python -m local_memory_chat.cli ask "your question" --profile demo
```

What it does:

```text
reads hot_address_index.jsonl
reads hot_counts.json
anchorizes the question
scores hot-memory records by anchor overlap and anchor pressure
writes a memory packet
writes a search receipt
prints a plain text result unless --json is used
```

It does not call a model.

It does not search the internet.

It does not use embeddings.

It does not read SQLite support binaries during ask.

It only searches the current hot address index.

## Ask Scoring

The current scoring code does this:

```text
question anchors = anchorize(question)
for each hot memory row:
  overlap = question anchors found in row anchors
  if no overlap, skip row
  pressure = sum(hot_counts.anchors[anchor] for each overlapping anchor)
  score = overlap_count * 10 + pressure
sort by:
  score descending
  timestamp ascending
  memory_id ascending
return top N
```

Default limit:

```text
5
```

You can change it:

```powershell
python -m local_memory_chat.cli ask "question" --profile demo --limit 10
```

## Memory Packets

Every ask writes a memory packet under:

```text
packets/
```

The packet contains:

```text
schema
created_at
question
memory_profile_id
search_policy
question_anchors
evidence_items
missing_evidence
render_policy
```

`search_policy` currently says:

```text
hot_searched=true
warm_searched=false
cold_searched=false
```

`render_policy` is:

```text
renderer_packet_only
```

That is a policy label only.

The current code does not call a renderer.

## Evidence Items

Each evidence item contains:

```text
memory_id
tier
source_type
source_label
timestamp
snippet
citation
score
matched_anchors
address
```

The address contains:

```text
source_id
chunk_id
line_start
line_end
char_start
char_end
```

This is how MEMCIT evidence can be checked against the source file.

## Receipts

Receipts are written under:

```text
receipts/
```

The code writes receipts for:

```text
demo intake
file intake
source attach
source index
binary inspect
SQLite support conversion
search
```

Search receipts include:

```text
question_hash
memory_packet_hash
memory_packet_path
evidence_count
memory_items_used
private_data_exported=false
```

## What Gets Hashed

The code uses SHA-256 for:

```text
source IDs
memory IDs
citations
file hashes
question hashes
packet hashes
row hashes
support binary hash
```

File hashing reads in chunks of 1 MB.

That avoids loading huge files all at once just to hash them.

## What Changes Original Sources

The code is written to read original sources, not modify them.

Receipts record:

```text
source_mutated=false
source_hash_before
source_hash_after
source_hash_unchanged
```

For live SQLite sources, the original attach hash may become stale because the source application keeps writing to the database.

The code can record that truth with:

```text
--allow-live-source
```

## What Is Not Implemented

From the code alone, these are not currently implemented:

```text
LLM rendering
OpenAI API calls
local model calls
warm memory
cold memory
lifetime binary counts
chat-binary turn decoding
direct ask search over SQLite support binaries
source echo filtering
packet verification command
full replay command
```

The code has support pieces for some of these ideas, but the commands above are the commands that actually exist now.

## How To Test Evidence Location Manually

For MEMCIT evidence:

```text
1. Run ask.
2. Open the packet JSON.
3. Pick an evidence item.
4. Read address.source_id.
5. Find that source_id in sources/source_manifest.jsonl.
6. Open the source path.
7. Compare snippet to the recorded line range.
8. Compare snippet to the recorded char range.
```

For SQLCIT evidence:

```text
1. Open support/sqlite_support_<source_id>.row_index.jsonl.
2. Pick a SQLCIT row.
3. Open binary_path.
4. Seek to binary_offset.
5. Read record_length bytes.
6. The first 4 bytes are the little-endian payload length.
7. Hash the JSON payload.
8. Compare it to row_hash.
9. Confirm payload citation and source_id match the row index.
```

## Plain English Data Flow

The current system works like this:

```text
source file or demo record
-> line chunks
-> anchors
-> hot address record with MEMCIT citation
-> hot counts
-> ask question
-> question anchors
-> overlap/pressure score
-> top evidence items
-> memory packet
-> search receipt
```

For SQLite support:

```text
attached SQLite file
-> read-only SQLite rows
-> length-prefixed support binary
-> SQLCIT row index
-> support receipt
```

These are two different lanes.

The ask command currently uses the hot address lane.

The SQLite support lane currently provides citeable supporting custody, not direct ask retrieval.
