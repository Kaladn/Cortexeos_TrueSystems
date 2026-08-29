#!/usr/bin/env python3
"""
PubMed XML to Text Converter

This script converts PubMed XML.gz files to plain text files, extracting
full text content while excluding pictures and picture-related text.

Usage:
    python pubmed_to_text.py <input_dir> <output_dir> [--workers N] [--chunk-size N]

Arguments:
    input_dir     Directory containing PubMed XML.gz files
    output_dir    Directory where text files will be saved
    --workers     Number of worker processes (default: auto-detect)
    --chunk-size  Number of files to process per worker batch (default: 10)
"""

import os
import sys
import time
import gzip
import argparse
import multiprocessing
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm

# Import pubmed_parser
try:
    import pubmed_parser as pp
except ImportError:
    print("Error: pubmed_parser package not found. Please install it with:")
    print("pip install pubmed_parser")
    sys.exit(1)

def extract_full_text(xml_file):
    """
    Extract full text content from a PubMed XML file
    
    Args:
        xml_file: Path to the XML file (can be gzipped)
        
    Returns:
        String containing the extracted text
    """
    try:
        # Read XML content
        if xml_file.endswith('.gz'):
            with gzip.open(xml_file, 'rb') as f:
                xml_content = f.read()
        else:
            with open(xml_file, 'rb') as f:
                xml_content = f.read()
        
        # Extract articles using the correct method
        articles = list(pp.parse_medline_xml(xml_content))
        
        if not articles:
            print(f"Warning: No articles found in {xml_file}")
            return ""
        
        # Combine all articles into a single text document
        full_text = []
        
        for article in articles:
            # Extract basic metadata
            pmid = article.get('pmid', '')
            title = article.get('title', '')
            abstract = article.get('abstract', '')
            authors = article.get('authors', '')
            journal = article.get('journal', '')
            
            # Skip if no title and abstract
            if not title and not abstract:
                continue
            
            # Format article text
            article_text = []
            
            if pmid:
                article_text.append(f"PMID: {pmid}")
            
            if title:
                article_text.append(f"TITLE: {title}")
            
            if journal:
                article_text.append(f"JOURNAL: {journal}")
            
            if authors:
                article_text.append(f"AUTHORS: {authors}")
            
            if abstract:
                article_text.append(f"ABSTRACT: {abstract}")
            
            # Add article to full text with separators
            full_text.append("\n".join(article_text))
            full_text.append("-" * 80)  # Add separator between articles
        
        return "\n\n".join(full_text)
    
    except Exception as e:
        print(f"Error processing {xml_file}: {e}")
        return ""

def process_file(args):
    """Process a single XML.gz file and save the extracted text"""
    input_file, output_dir = args
    try:
        # Create output filename
        input_path = Path(input_file)
        output_file = Path(output_dir) / f"{input_path.stem.split('.')[0]}.txt"
        
        # Extract text
        start_time = time.time()
        full_text = extract_full_text(input_file)
        
        # Save to file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(full_text)
        
        elapsed = time.time() - start_time
        print(f"Processed {input_file} → {output_file} ({elapsed:.2f}s)")
        return True
    
    except Exception as e:
        print(f"Error processing {input_file}: {e}")
        return False

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert PubMed XML.gz files to text')
    parser.add_argument('input_dir', help='Directory containing PubMed XML.gz files')
    parser.add_argument('output_dir', help='Directory where text files will be saved')
    parser.add_argument('--workers', type=int, default=None, 
                        help='Number of worker processes (default: auto-detect)')
    parser.add_argument('--chunk-size', type=int, default=10,
                        help='Number of files to process per worker batch (default: 10)')
    args = parser.parse_args()
    
    # Validate directories
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: Input directory '{input_dir}' does not exist")
        return 1
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all XML.gz files
    xml_files = []
    for ext in ['.xml.gz', '.xml']:
        xml_files.extend(list(input_dir.glob(f'**/*{ext}')))
    
    if not xml_files:
        print(f"No XML files found in {input_dir}")
        return 1
    
    print(f"Found {len(xml_files)} XML files to process")
    
    # Determine number of workers
    if args.workers is None:
        # For i9-13900K with 24 cores (8P + 16E), use 80% of physical cores
        # This leaves some resources for system tasks
        num_workers = max(1, int(multiprocessing.cpu_count() * 0.8))
    else:
        num_workers = args.workers
    
    print(f"Using {num_workers} worker processes")
    
    # Process files in parallel with chunking for better performance
    start_time = time.time()
    
    # Create progress bar
    progress_bar = tqdm(
        total=len(xml_files),
        desc="Converting XML to Text",
        unit="file",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
    )
    
    # Process files in parallel
    success_count = 0
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        args_list = [(str(f), str(output_dir)) for f in xml_files]
        # Use chunksize parameter for better performance with many small tasks
        for result in executor.map(process_file, args_list, chunksize=args.chunk_size):
            if result:
                success_count += 1
            progress_bar.update(1)
    
    # Close progress bar
    progress_bar.close()
    
    # Report results
    elapsed = time.time() - start_time
    
    print(f"\nProcessing complete!")
    print(f"Successfully processed {success_count} of {len(xml_files)} files")
    print(f"Total time: {elapsed:.2f} seconds")
    print(f"Average time per file: {elapsed/len(xml_files):.2f} seconds")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())