import spacy
import re
import logging
import torch
import os
import sys
import xml.etree.ElementTree as ET
from multiprocessing import Pool, cpu_count, set_start_method
import time
import gzip
import psutil

# Configure logging to a file
logging.basicConfig(
 level=logging.INFO,
 format='%(asctime)s - %(levelname)s - %(message)s',
 handlers=[logging.FileHandler("processing.log")]
)

# Check for GPU availability
def setup_gpu():
 if torch.cuda.is_available():
 device = torch.device('cuda')
 logging.info(f"Using CUDA GPU: {torch.cuda.get_device_name(0)}")
 return 'cuda'
 else:
 try:
 if hasattr(torch, 'hip') and torch.hip.is_available():
 device = torch.device('hip')
 logging.info(f"Using ROCm (AMD GPU): {torch.hip.get_device_name(0)}")
 return 'rocm'
 else:
 logging.warning("No GPU acceleration available. Using CPU.")
 return 'cpu'
 except:
 logging.warning("No GPU acceleration available. Using CPU.")
 return 'cpu'

# Set up device
device_type = setup_gpu()

# Compile regex patterns (used as fallback)
RE_AUTHOR = re.compile(r"^(.*?)(?:\.|;)\s*\(")
RE_TITLE = re.compile(r"\(\d{4}\)\.\s*(?:\"(.*?)\"|'(.*?)'|(.*?)\.)")
RE_YEAR = re.compile(r"\((\d{4})\)")

def format_pubmed_citation(article):
 """
 Format a PubMed article into a citation-like string and extract entities directly.
 Returns (citation string, entities dict).
 """
 try:
 title_elem = article.find(".//ArticleTitle")
 authors = article.findall(".//Author")
 journal_elem = article.find(".//Journal/Title")
 year_elem = article.find(".//PubDate/Year")
 volume_elem = article.find(".//JournalIssue/Volume")
 issue_elem = article.find(".//JournalIssue/Issue")
 pages_elem = article.find(".//Pagination/MedlinePgn")

 entities = {}

 # Authors
 author_str = ""
 if authors:
 author_list = []
 for author in authors[:3]:
 last_name = author.find("LastName")
 initials = author.find("Initials")
 if last_name is not None and initials is not None:
 author_list.append(f"{last_name.text}, {initials.text}")
 author_str = ", ".join(author_list)
 if len(authors) > 3:
 author_str += " et al."
 entities["author"] = author_str

 # Year
 year_str = year_elem.text if year_elem is not None else ""
 if year_str:
 entities["year"] = year_str

 # Title
 title_str = f'"{title_elem.text}"' if title_elem is not None and title_elem.text else ""
 if title_str:
 entities["title"] = title_elem.text

 # Journal, Volume, Issue, Pages
 if journal_elem is not None and journal_elem.text:
 entities["journal"] = journal_elem.text
 if volume_elem is not None and volume_elem.text:
 entities["volume"] = volume_elem.text
 if issue_elem is not None and issue_elem.text:
 entities["issue"] = issue_elem.text
 if pages_elem is not None and pages_elem.text:
 entities["pages"] = pages_elem.text

 # Build citation string
 parts = [
 author_str,
 f"({year_str})" if year_str else "",
 title_str,
 entities.get("journal", ""),
 entities.get("volume", ""),
 f"({entities.get('issue', '')})" if entities.get("issue") else "",
 entities.get("pages", "")
 ]
 citation = ". ".join(part for part in parts if part)

 return citation, entities if entities else {}
 except Exception as e:
 logging.error(f"Error formatting PubMed citation: {e}")
 return "", {}

def extract_entities_batch(citation_batch):
 """
 Process a batch of citations in memory.
 Returns a list of (citation, entities) tuples.
 """
 results = []
 for citation_data, filepath in citation_batch:
 if isinstance(citation_data, ET.Element):
 citation, entities = format_pubmed_citation(citation_data)
 results.append((citation, entities))
 else:
 citation_text = citation_data
 entities = {}
 try:
 author_match = RE_AUTHOR.match(citation_text)
 if author_match:
 entities["author"] = author_match.group(1).strip()

 title_match = RE_TITLE.search(citation_text)
 if title_match:
 title_groups = [g for g in title_match.groups() if g is not None]
 if title_groups:
 entities["title"] = title_groups[0].strip()

 year_match = RE_YEAR.search(citation_text)
 if year_match:
 entities["year"] = year_match.group(1)

 results.append((citation_text, entities))
 except Exception as e:
 logging.error(f"Error extracting entities from citation: {citation_text} - Error: {e}")
 results.append((citation_text, {}))
 
 return results

def load_citations_into_ram(files, max_ram_bytes=15 * 1024 * 1024 * 1024):
 """
 Load citations into RAM up to max_ram_bytes (default 15GB).
 Returns a list of (citation_data, filepath) tuples and remaining files.
 """
 citations = []
 ram_used = 0
 processed_files = []

 for filepath in files:
 logging.info(f"Attempting to load file: {filepath}")
 try:
 # Check for .xml.gz explicitly
 if filepath.lower().endswith(".xml.gz"):
 with gzip.open(filepath, 'rb') as file:
 context = ET.iterparse(file, events=("start", "end"))
 context = iter(context)
 event, root = next(context)
 for event, elem in context:
 if event == "end" and elem.tag == "PubmedArticle":
 citation_data = elem
 size_estimate = sys.getsizeof(citation_data) + 1000 # Buffer for attributes
 if ram_used + size_estimate > max_ram_bytes:
 logging.info(f"RAM limit reached at {ram_used / (1024 * 1024 * 1024):.2f}GB")
 return citations, [filepath] + files[len(processed_files) + 1:]
 citations.append((citation_data, filepath))
 ram_used += size_estimate
 elem.clear()
 root.clear()
 logging.info(f"Loaded { len(citations) - sum(1 for f in processed_files if f == filepath)} citations from {filepath}")
 processed_files.append(filepath)
 except Exception as e:
 logging.error(f"Error loading file {filepath}: {e}")
 
 logging.info(f"Loaded all citations from {len(processed_files)} files")
 return citations, []

def process_files(input_directory, output_file, bad_citations_file, batch_size=1000, num_workers=None, max_ram=15):
 """
 Process files by loading into RAM, extracting in memory, and appending in chunks.
 """
 start_time = time.time()

 # Focus on .xml.gz for PubMed
 files = [f for f in os.listdir(input_directory) if f.lower().endswith(".xml.gz")]
 total_files = len(files)

 if total_files == 0:
 print("No supported files (.xml.gz) found in the directory.")
 return

 if num_workers is None:
 num_workers = max(1, cpu_count() - 1)
 logging.info(f"Using {num_workers} workers for parallel processing")

 total_citations = 0
 citations_processed = 0
 processed_files = 0
 max_ram_bytes = max_ram * 1024 * 1024 * 1024 # Convert GB to bytes

 remaining_files = files.copy()

 with open(output_file, 'a', encoding='utf-8') as out_f, \
 open(bad_citations_file, 'a', encoding='utf-8') as bad_f:
 if os.stat(output_file).st_size == 0:
 out_f.write(f"Processing results using device: {device_type}\n\n")
 if os.stat(bad_citations_file).st_size == 0:
 bad_f.write("Citations with no extracted entities (for human review):\n\n")

 while remaining_files:
 # Load citations into RAM
 citations, remaining_files = load_citations_into_ram(remaining_files, max_ram_bytes)
 file_count = len(files) - len(remaining_files)
 total_citations += len(citations)

 if not citations:
 logging.error("No citations loaded into RAM; check file format or content.")
 break

 # Process citations in memory in batches
 citation_iter = iter(citations)
 while True:
 batch = list(islice(citation_iter, batch_size))
 if not batch:
 break

 with Pool(processes=num_workers) as pool:
 chunk_size = max(1, len(batch) // num_workers)
 chunks = [batch[i:i + chunk_size] for i in range(0, len(batch), chunk_size)]
 results = pool.map(extract_entities_batch, chunks)

 for chunk_result in results:
 for citation_text, entities in chunk_result:
 if entities:
 out_f.write(f"Citation: {citation_text}\nExtracted Entities: {entities}\n\n")
 citations_processed += 1
 else:
 bad_f.write(f"Citation: {citation_text}\n\n")

 # Update live counter
 elapsed_time = time.time() - start_time
 ram_usage = psutil.Process().memory_info().rss / (1024 * 1024 * 1024) # GB
 sys.stdout.write(
 f"\rFiles: {file_count}/{total_files} | "
 f"Citations Found: {total_citations} | "
 f"Processed: {citations_processed} | "
 f"Time: {elapsed_time:.1f}s | "
 f"RAM: {ram_usage:.1f}GB"
 )
 sys.stdout.flush()

 processed_files = file_count
 del citations # Free RAM for next chunk

 elapsed_time = time.time() - start_time
 citations_per_second = citations_processed / elapsed_time if elapsed_time > 0 else 0

 # Final summary
 print(f"\n\nProcessing complete! Results written to: {output_file}")
 print(f"Bad citations logged to: {bad_citations_file}")
 print("\nSummary:")
 print(f"Total Files Processed: {total_files}")
 print(f"Total Citations Found: {total_citations}")
 print(f"Total Citations Successfully Processed: {citations_processed}")
 print(f"Elapsed Time: {elapsed_time:.2f} seconds")
 print(f"Processing Rate: {citations_per_second:.2f} citations/second")

if __name__ == "__main__":
 set_start_method('spawn', force=True)

 input_directory = input("Enter the full input directory path to citation files: ")
 if not os.path.isdir(input_directory):
 logging.error(f"The provided directory does not exist: {input_directory}")
 print(f"Error: The directory {input_directory} does not exist.")
 else:
 logging.info(f"Processing citation files from: {input_directory}")
 print(f"Using device: {device_type}")
 
 output_file = os.path.join(input_directory, "extracted_entities.txt")
 bad_citations_file = os.path.join(input_directory, "bad_citations.txt")
 
 process_files(input_directory, output_file, bad_citations_file, batch_size=1000, num_workers=None, max_ram=15)