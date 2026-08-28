"""
Data Loader Module
Handles data ingestion and initial processing
"""

import os
from typing import Any, Dict, List, Union

class DataLoader:
    """Handles loading and initial processing of data samples"""
    
    def __init__(self):
        self.supported_formats = ['txt', 'csv', 'json', 'fasta']
    
    def load_data(self, file_path: str) -> Union[str, List[str], Dict]:
        """
        Load data from file based on format
        
        Args:
            file_path: Path to data file
            
        Returns:
            Loaded data in appropriate format
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Data file not found: {file_path}")
        
        file_extension = file_path.split('.')[-1].lower()
        
        if file_extension == 'txt':
            return self._load_text_file(file_path)
        elif file_extension == 'csv':
            return self._load_csv_file(file_path)
        elif file_extension == 'json':
            return self._load_json_file(file_path)
        elif file_extension in ['fasta', 'fa']:
            return self._load_fasta_file(file_path)
        else:
            # Default to text loading
            return self._load_text_file(file_path)
    
    def _load_text_file(self, file_path: str) -> str:
        """Load plain text file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _load_csv_file(self, file_path: str) -> List[Dict]:
        """Load CSV file"""
        import csv
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return data
    
    def _load_json_file(self, file_path: str) -> Dict:
        """Load JSON file"""
        import json
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_fasta_file(self, file_path: str) -> Dict[str, str]:
        """Load FASTA file for genome data"""
        sequences = {}
        current_id = None
        current_seq = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('>'):
                    if current_id:
                        sequences[current_id] = ''.join(current_seq)
                    current_id = line[1:]
                    current_seq = []
                else:
                    current_seq.append(line)
            
            if current_id:
                sequences[current_id] = ''.join(current_seq)
        
        return sequences
    
    def validate_data(self, data: Any, data_type: str) -> bool:
        """
        Validate loaded data against expected type
        
        Args:
            data: Loaded data
            data_type: Expected data type from config
            
        Returns:
            True if valid, False otherwise
        """
        if data_type == 'genome':
            return self._validate_genome_data(data)
        elif data_type == 'text':
            return isinstance(data, str)
        elif data_type == 'tabular':
            return isinstance(data, list) and all(isinstance(row, dict) for row in data)
        else:
            return True  # Unknown types pass validation
    
    def _validate_genome_data(self, data: Any) -> bool:
        """Validate genome sequence data"""
        if isinstance(data, str):
            # Check if string contains valid nucleotides
            valid_chars = set('ATCGN')
            return all(c.upper() in valid_chars for c in data if c.isalpha())
        elif isinstance(data, dict):
            # FASTA format validation
            return all(isinstance(seq, str) for seq in data.values())
        return False

