"""
CompuCog ChatGPT Conversation Adapter
Parses ChatGPT HTML exports and converts to symbol events for temporal analysis
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from bs4 import BeautifulSoup


class ChatGPTAdapter:
    """
    Converts ChatGPT conversation history (HTML export) to symbol events.
    
    Tracks:
    - Model versions (GPT-3.5, GPT-4, GPT-4o, etc.)
    - Message patterns (length, quality, errors)
    - Conversation flow (topic shifts, breaks)
    - Temporal changes (when things broke)
    """
    
    def __init__(self, genome_path: str, output_dir: str = "data/symbols"):
        self.genome_path = Path(genome_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load genome
        self.genome = self._load_genome()
        
        # Statistics
        self.stats = {
            "conversations_processed": 0,
            "messages_processed": 0,
            "events_created": 0,
            "model_changes_detected": 0,
            "errors": 0
        }
    
    def _load_genome(self) -> Dict:
        """Load conversation genome mapping file"""
        if not self.genome_path.exists():
            raise FileNotFoundError(f"Genome file not found: {self.genome_path}")
        
        with open(self.genome_path, 'r') as f:
            genome = json.load(f)
        
        print(f"[ChatGPTAdapter] Loaded genome: {genome.get('name', 'Unknown')}")
        return genome
    
    def ingest(self, source: str, entity: str = None) -> int:
        """
        Ingest ChatGPT conversation history from HTML export.
        
        Args:
            source: Path to HTML file (ChatGPT export)
            entity: Conversation ID or name. If None, derived from filename.
        
        Returns:
            Number of events created
        """
        source_path = Path(source)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source}")
        
        # Derive entity from filename if not provided
        if entity is None:
            entity = source_path.stem
        
        print(f"[ChatGPTAdapter] Ingesting {source} for conversation: {entity}")
        
        # Parse HTML
        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            soup = BeautifulSoup(html_content, 'html.parser')
        except Exception as e:
            print(f"[ChatGPTAdapter] Error reading HTML: {e}")
            self.stats["errors"] += 1
            return 0
        
        # Extract conversations
        conversations = self._extract_conversations(soup)
        
        # Output file
        output_file = self.output_dir / "chatgpt_symbols.jsonl"
        
        # Process each conversation
        with open(output_file, 'a') as f:  # Append mode
            for conv in conversations:
                try:
                    # Convert conversation to symbols
                    events = self._conversation_to_symbols(conv, entity)
                    
                    # Write events
                    for event in events:
                        f.write(json.dumps(event) + '\n')
                        self.stats["events_created"] += 1
                    
                    self.stats["conversations_processed"] += 1
                    
                except Exception as e:
                    print(f"[ChatGPTAdapter] Error processing conversation: {e}")
                    self.stats["errors"] += 1
        
        print(f"[ChatGPTAdapter] Ingestion complete. Stats: {self.stats}")
        return self.stats["events_created"]
    
    def _extract_conversations(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Extract conversations from ChatGPT HTML export.
        
        Returns list of conversation dicts with:
        - timestamp: Unix timestamp
        - role: 'user' or 'assistant'
        - content: Message text
        - model: Model version (if detected)
        """
        conversations = []
        
        # ChatGPT HTML structure varies, try multiple patterns
        # Pattern 1: <div class="message"> with data-message-author-role
        messages = soup.find_all('div', class_='message')
        
        if not messages:
            # Pattern 2: <div> with role attribute
            messages = soup.find_all('div', attrs={'role': lambda x: x in ['user', 'assistant']})
        
        if not messages:
            # Pattern 3: Generic text-based parsing
            print("[ChatGPTAdapter] Warning: Could not find structured messages, attempting text parsing")
            return self._parse_text_format(soup.get_text())
        
        for msg in messages:
            try:
                # Extract role
                role = msg.get('data-message-author-role') or msg.get('role') or 'unknown'
                
                # Extract content
                content = msg.get_text(strip=True)
                
                # Extract timestamp (if available)
                timestamp_elem = msg.find('time') or msg.find(class_='timestamp')
                if timestamp_elem:
                    timestamp_str = timestamp_elem.get('datetime') or timestamp_elem.get_text()
                    timestamp = self._parse_timestamp(timestamp_str)
                else:
                    # Use current time if no timestamp
                    timestamp = int(datetime.now().timestamp())
                
                # Detect model version from content or metadata
                model = self._detect_model(msg, content)
                
                conversations.append({
                    'timestamp': timestamp,
                    'role': role,
                    'content': content,
                    'model': model
                })
                
                self.stats["messages_processed"] += 1
                
            except Exception as e:
                print(f"[ChatGPTAdapter] Error parsing message: {e}")
                continue
        
        return conversations
    
    def _parse_text_format(self, text: str) -> List[Dict]:
        """
        Fallback: Parse plain text format.
        Looks for patterns like "User:" and "Assistant:" or timestamps.
        """
        conversations = []
        lines = text.split('\n')
        
        current_role = None
        current_content = []
        current_timestamp = int(datetime.now().timestamp())
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect role changes
            if line.lower().startswith('user:') or line.lower().startswith('you:'):
                if current_role and current_content:
                    conversations.append({
                        'timestamp': current_timestamp,
                        'role': current_role,
                        'content': ' '.join(current_content),
                        'model': 'unknown'
                    })
                current_role = 'user'
                current_content = [line.split(':', 1)[1].strip()]
            
            elif line.lower().startswith('assistant:') or line.lower().startswith('chatgpt:'):
                if current_role and current_content:
                    conversations.append({
                        'timestamp': current_timestamp,
                        'role': current_role,
                        'content': ' '.join(current_content),
                        'model': 'unknown'
                    })
                current_role = 'assistant'
                current_content = [line.split(':', 1)[1].strip()]
            
            else:
                # Continue current message
                if current_role:
                    current_content.append(line)
        
        # Add last message
        if current_role and current_content:
            conversations.append({
                'timestamp': current_timestamp,
                'role': current_role,
                'content': ' '.join(current_content),
                'model': 'unknown'
            })
        
        return conversations
    
    def _parse_timestamp(self, timestamp_str: str) -> int:
        """Parse timestamp string to Unix timestamp"""
        try:
            # Try ISO format
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return int(dt.timestamp())
        except:
            try:
                # Try common formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y']:
                    try:
                        dt = datetime.strptime(timestamp_str, fmt)
                        return int(dt.timestamp())
                    except:
                        continue
            except:
                pass
        
        # Default to current time
        return int(datetime.now().timestamp())
    
    def _detect_model(self, msg_elem, content: str) -> str:
        """Detect model version from message metadata or content"""
        # Check for model in metadata
        model = msg_elem.get('data-model') or msg_elem.get('model')
        if model:
            return model
        
        # Check for model mentions in content
        content_lower = content.lower()
        if 'gpt-4o' in content_lower or 'gpt4o' in content_lower:
            return 'gpt-4o'
        elif 'gpt-4' in content_lower or 'gpt4' in content_lower:
            return 'gpt-4'
        elif 'gpt-3.5' in content_lower or 'gpt3.5' in content_lower:
            return 'gpt-3.5-turbo'
        
        return 'unknown'
    
    def _conversation_to_symbols(self, conv: Dict, entity: str) -> List[Dict]:
        """
        Convert conversation message to symbol events.
        
        Generates symbols for:
        - Message length (SHORT/MED/LONG/VLONG)
        - Role (USER/ASSISTANT)
        - Model version (GPT35/GPT4/GPT4O)
        - Quality indicators (ERROR/INCOMPLETE/GOOD)
        """
        events = []
        timestamp = conv['timestamp']
        
        # Role symbol
        role_symbol = f"role_{conv['role'].upper()}"
        events.append({
            "timestamp": timestamp,
            "entity": entity,
            "symbol": role_symbol,
            "genome": "chatgpt_conversation",
            "value": 1.0,
            "metadata": {"type": "role"}
        })
        
        # Model symbol
        model_symbol = self._map_model_to_symbol(conv['model'])
        events.append({
            "timestamp": timestamp,
            "entity": entity,
            "symbol": model_symbol,
            "genome": "chatgpt_conversation",
            "value": 1.0,
            "metadata": {"type": "model", "model": conv['model']}
        })
        
        # Length symbol
        length_symbol = self._map_length_to_symbol(len(conv['content']))
        events.append({
            "timestamp": timestamp,
            "entity": entity,
            "symbol": length_symbol,
            "genome": "chatgpt_conversation",
            "value": float(len(conv['content'])),
            "metadata": {"type": "length"}
        })
        
        # Quality symbol (for assistant messages)
        if conv['role'] == 'assistant':
            quality_symbol = self._assess_quality(conv['content'])
            events.append({
                "timestamp": timestamp,
                "entity": entity,
                "symbol": quality_symbol,
                "genome": "chatgpt_conversation",
                "value": 1.0,
                "metadata": {"type": "quality"}
            })
        
        return events
    
    def _map_model_to_symbol(self, model: str) -> str:
        """Map model version to symbol"""
        model_lower = model.lower()
        if 'gpt-4o' in model_lower or 'gpt4o' in model_lower:
            return "model_GPT4O"
        elif 'gpt-4' in model_lower or 'gpt4' in model_lower:
            return "model_GPT4"
        elif 'gpt-3.5' in model_lower or 'gpt3.5' in model_lower:
            return "model_GPT35"
        else:
            return "model_UNKNOWN"
    
    def _map_length_to_symbol(self, length: int) -> str:
        """Map message length to symbol"""
        if length < 100:
            return "length_SHORT"
        elif length < 500:
            return "length_MED"
        elif length < 2000:
            return "length_LONG"
        else:
            return "length_VLONG"
    
    def _assess_quality(self, content: str) -> str:
        """Assess response quality based on content patterns"""
        content_lower = content.lower()
        
        # Error indicators
        if any(err in content_lower for err in ['error', 'sorry', 'cannot', "can't", 'unable']):
            return "quality_ERROR"
        
        # Incomplete indicators
        if content.endswith('...') or len(content) < 50:
            return "quality_INCOMPLETE"
        
        # Good response (default)
        return "quality_GOOD"
    
    def get_statistics(self) -> Dict:
        """Return ingestion statistics"""
        return self.stats


if __name__ == "__main__":
    # Test the adapter
    print("ChatGPTAdapter test mode")
    print("Export your ChatGPT conversations to HTML and test ingestion")
