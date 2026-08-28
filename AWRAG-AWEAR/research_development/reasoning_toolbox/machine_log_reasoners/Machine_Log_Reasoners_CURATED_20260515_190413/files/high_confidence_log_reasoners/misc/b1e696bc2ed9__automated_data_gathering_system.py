"""
Automated Data Gathering System for Kali Ka

This system automates the collection of educational materials and experiential data
for Kali Ka, supporting both formal knowledge acquisition and experiential learning.

The system includes:
1. Web Scraping Module - For collecting data from websites, academic repositories, etc.
2. API Integration Module - For accessing structured data from various APIs
3. Media Processing Module - For processing books, videos, and other media
4. Data Validation Module - For ensuring quality and relevance of gathered data
5. Scheduling and Orchestration - For managing the data gathering process

Author: Manus
Date: April 8, 2025
"""

import os
import time
import json
import random
import hashlib
import urllib.request
import urllib.parse
from datetime import datetime
from threading import Thread
from queue import Queue
import re

# Create necessary directories
os.makedirs('/home/ubuntu/nexus_project/data_gathering', exist_ok=True)
os.makedirs('/home/ubuntu/nexus_project/data_gathering/raw', exist_ok=True)
os.makedirs('/home/ubuntu/nexus_project/data_gathering/processed', exist_ok=True)
os.makedirs('/home/ubuntu/nexus_project/data_gathering/validated', exist_ok=True)
os.makedirs('/home/ubuntu/nexus_project/data_gathering/logs', exist_ok=True)

# Configuration
CONFIG = {
    'max_threads': 5,
    'request_delay': 1.5,  # seconds between requests to same domain
    'max_retries': 3,
    'user_agent': 'KaliKa-DataGatherer/1.0',
    'log_level': 'INFO',
    'validation_threshold': 0.7,  # minimum quality score to accept data
    'domains': {
        'security': {
            'priority': 1,
            'sources': [
                {'type': 'web', 'url': 'https://www.nist.gov/cyberframework', 'depth': 2},
                {'type': 'api', 'endpoint': 'https://services.nvd.nist.gov/rest/json/cves/2.0', 'params': {'resultsPerPage': 10}},
                {'type': 'web', 'url': 'https://owasp.org/www-project-top-ten/', 'depth': 2}
            ]
        },
        'ai_ethics': {
            'priority': 2,
            'sources': [
                {'type': 'web', 'url': 'https://www.ieee.org/ethics', 'depth': 2},
                {'type': 'web', 'url': 'https://ai.google/principles/', 'depth': 1},
                {'type': 'web', 'url': 'https://www.partnershiponai.org/resources/', 'depth': 2}
            ]
        },
        'computer_science': {
            'priority': 3,
            'sources': [
                {'type': 'web', 'url': 'https://ocw.mit.edu/courses/electrical-engineering-and-computer-science/', 'depth': 2},
                {'type': 'api', 'endpoint': 'https://api.github.com/search/repositories', 'params': {'q': 'data structures', 'sort': 'stars'}},
                {'type': 'web', 'url': 'https://www.geeksforgeeks.org/data-structures/', 'depth': 2}
            ]
        },
        'critical_thinking': {
            'priority': 4,
            'sources': [
                {'type': 'web', 'url': 'https://plato.stanford.edu/entries/critical-thinking/', 'depth': 1},
                {'type': 'web', 'url': 'https://yourlogicalfallacyis.com/', 'depth': 2},
                {'type': 'web', 'url': 'https://www.criticalthinking.org/pages/defining-critical-thinking/766', 'depth': 2}
            ]
        }
    }
}

# Logging setup
class Logger:
    def __init__(self, name, level='INFO'):
        self.name = name
        self.level = level
        self.log_file = f"/home/ubuntu/nexus_project/data_gathering/logs/{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        with open(self.log_file, 'w') as f:
            f.write(f"=== {name} Log Started at {datetime.now()} ===\n")
    
    def log(self, message, level='INFO'):
        if self._should_log(level):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"[{timestamp}] [{level}] {message}"
            
            with open(self.log_file, 'a') as f:
                f.write(log_entry + '\n')
            
            if level in ['ERROR', 'CRITICAL']:
                print(log_entry)
    
    def _should_log(self, level):
        levels = {'DEBUG': 0, 'INFO': 1, 'WARNING': 2, 'ERROR': 3, 'CRITICAL': 4}
        return levels.get(level, 0) >= levels.get(self.level, 1)
    
    def info(self, message):
        self.log(message, 'INFO')
    
    def debug(self, message):
        self.log(message, 'DEBUG')
    
    def warning(self, message):
        self.log(message, 'WARNING')
    
    def error(self, message):
        self.log(message, 'ERROR')
    
    def critical(self, message):
        self.log(message, 'CRITICAL')

# Main logger
logger = Logger('data_gatherer', CONFIG['log_level'])

# Base Data Gatherer
class DataGatherer:
    def __init__(self, domain, source):
        self.domain = domain
        self.source = source
        self.data_queue = Queue()
        self.domain_timestamps = {}
    
    def gather(self):
        """Base gather method to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement gather()")
    
    def _respect_rate_limits(self, domain):
        """Ensure we don't overwhelm sources with requests"""
        current_time = time.time()
        if domain in self.domain_timestamps:
            elapsed = current_time - self.domain_timestamps[domain]
            if elapsed < CONFIG['request_delay']:
                time.sleep(CONFIG['request_delay'] - elapsed)
        
        self.domain_timestamps[domain] = time.time()
    
    def _generate_filename(self, content, extension):
        """Generate a unique filename based on content hash"""
        content_hash = hashlib.md5(str(content).encode()).hexdigest()[:10]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{self.domain}_{timestamp}_{content_hash}.{extension}"
    
    def _save_raw_data(self, data, extension='json'):
        """Save raw data to file system"""
        if not data:
            return None
            
        filename = self._generate_filename(data, extension)
        filepath = f"/home/ubuntu/nexus_project/data_gathering/raw/{filename}"
        
        try:
            if extension == 'json':
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
            else:
                with open(filepath, 'w') as f:
                    f.write(data)
            
            logger.info(f"Saved raw data to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving raw data: {str(e)}")
            return None

# Web Scraper
class WebScraper(DataGatherer):
    def __init__(self, domain, source):
        super().__init__(domain, source)
        self.url = source['url']
        self.depth = source.get('depth', 1)
        self.visited_urls = set()
    
    def gather(self):
        """Gather data from web sources"""
        logger.info(f"Starting web scraping for {self.url} with depth {self.depth}")
        self._scrape_url(self.url, self.depth)
        return True
    
    def _scrape_url(self, url, depth):
        """Recursively scrape URLs up to specified depth"""
        if depth <= 0 or url in self.visited_urls:
            return
        
        self.visited_urls.add(url)
        domain = urllib.parse.urlparse(url).netloc
        self._respect_rate_limits(domain)
        
        try:
            logger.info(f"Scraping {url}")
            req = urllib.request.Request(url, headers={'User-Agent': CONFIG['user_agent']})
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8')
                
            # Save the raw HTML
            filepath = self._save_raw_data(html, 'html')
            if filepath:
                # Extract text content (simplified)
                text_content = self._extract_text(html)
                
                # Create metadata
                metadata = {
                    'source_url': url,
                    'domain': self.domain,
                    'timestamp': datetime.now().isoformat(),
                    'content_type': 'text/html',
                    'raw_filepath': filepath
                }
                
                # Add to processing queue
                self.data_queue.put({
                    'content': text_content,
                    'metadata': metadata,
                    'type': 'web'
                })
                
                # Extract links for further scraping if depth allows
                if depth > 1:
                    links = self._extract_links(html, url)
                    for link in links[:5]:  # Limit to 5 links per page for demo
                        self._scrape_url(link, depth - 1)
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
    
    def _extract_text(self, html):
        """Extract main text content from HTML (simplified)"""
        # Remove scripts, styles, and HTML tags
        text = re.sub(r'<script.*?>.*?</script>', ' ', html, flags=re.DOTALL)
        text = re.sub(r'<style.*?>.*?</style>', ' ', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _extract_links(self, html, base_url):
        """Extract links from HTML content"""
        links = []
        base_domain = urllib.parse.urlparse(base_url).netloc
        
        # Simple regex for href extraction
        href_pattern = re.compile(r'href=["\'](.*?)["\']')
        for match in href_pattern.finditer(html):
            link = match.group(1)
            
            # Handle relative URLs
            if not link.startswith(('http://', 'https://')):
                if link.startswith('/'):
                    parsed_base = urllib.parse.urlparse(base_url)
                    link = f"{parsed_base.scheme}://{parsed_base.netloc}{link}"
                else:
                    link = urllib.parse.urljoin(base_url, link)
            
            # Only include links from same domain
            if urllib.parse.urlparse(link).netloc == base_domain:
                links.append(link)
        
        return list(set(links))  # Remove duplicates

# API Data Gatherer
class ApiGatherer(DataGatherer):
    def __init__(self, domain, source):
        super().__init__(domain, source)
        self.endpoint = source['endpoint']
        self.params = source.get('params', {})
    
    def gather(self):
        """Gather data from API endpoints"""
        logger.info(f"Starting API gathering for {self.endpoint}")
        
        domain = urllib.parse.urlparse(self.endpoint).netloc
        self._respect_rate_limits(domain)
        
        try:
            # Build URL with parameters
            url = self.endpoint
            if self.params:
                query_string = urllib.parse.urlencode(self.params)
                url = f"{url}?{query_string}"
            
            # Make request
            req = urllib.request.Request(url, headers={'User-Agent': CONFIG['user_agent']})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            # Save raw data
            filepath = self._save_raw_data(data, 'json')
            if filepath:
                # Create metadata
                metadata = {
                    'source_url': url,
                    'domain': self.domain,
                    'timestamp': datetime.now().isoformat(),
                    'content_type': 'application/json',
                    'raw_filepath': filepath
                }
                
                # Add to processing queue
                self.data_queue.put({
                    'content': data,
                    'metadata': metadata,
                    'type': 'api'
                })
            
            return True
            
        except Exception as e:
            logger.error(f"Error gathering from API {self.endpoint}: {str(e)}")
            return False

# Data Processor
class DataProcessor:
    def __init__(self, data_queue):
        self.data_queue = data_queue
        self.processed_data = []
    
    def process(self):
        """Process data from the queue"""
        while not self.data_queue.empty():
            data_item = self.data_queue.get()
            
            try:
                processed_item = self._process_item(data_item)
                if processed_item:
                    self.processed_data.append(processed_item)
                    self._save_processed_data(processed_item)
            except Exception as e:
                logger.error(f"Error processing data: {str(e)}")
            
            self.data_queue.task_done()
    
    def _process_item(self, data_item):
        """Process a single data item based on its type"""
        content_type = data_item['type']
        
        if content_type == 'web':
            return self._process_web_content(data_item)
        elif content_type == 'api':
            return self._process_api_content(data_item)
        else:
            logger.warning(f"Unknown content type: {content_type}")
            return None
    
    def _process_web_content(self, data_item):
        """Process web content (HTML)"""
        content = data_item['content']
        metadata = data_item['metadata']
        
        # Extract key information (simplified)
        # In a real implementation, this would use NLP to extract structured information
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        # Create processed item
        processed_item = {
            'content': {
                'text': content,
                'paragraphs': paragraphs[:10],  # First 10 paragraphs
                'summary': ' '.join(paragraphs[:2]) if paragraphs else ''  # Simple summary
            },
            'metadata': metadata,
            'processing': {
                'timestamp': datetime.now().isoformat(),
                'extracted_paragraphs': len(paragraphs)
            }
        }
        
        return processed_item
    
    def _process_api_content(self, data_item):
        """Process API content (JSON)"""
        content = data_item['content']
        metadata = data_item['metadata']
        
        # Create processed item
        processed_item = {
            'content': content,
            'metadata': metadata,
            'processing': {
                'timestamp': datetime.now().isoformat(),
                'structure': self._analyze_structure(content)
            }
        }
        
        return processed_item
    
    def _analyze_structure(self, content):
        """Analyze the structure of JSON content"""
        if isinstance(content, dict):
            return {k: type(v).__name__ for k, v in content.items()}
        elif isinstance(content, list) and content:
            return {
                'type': 'list',
                'length': len(content),
                'sample': type(content[0]).__name__ if content else None
            }
        else:
            return {'type': type(content).__name__}
    
    def _save_processed_data(self, processed_item):
        """Save processed data to file system"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        domain = processed_item['metadata']['domain']
        content_hash = hashlib.md5(str(processed_item).encode()).hexdigest()[:10]
        
        filename = f"{domain}_{timestamp}_{content_hash}.json"
        filepath = f"/home/ubuntu/nexus_project/data_gathering/processed/{filename}"
        
        try:
            with open(filepath, 'w') as f:
                json.dump(processed_item, f, indent=2)
            
            logger.info(f"Saved processed data to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving processed data: {str(e)}")
            return None

# Data Validator
class DataValidator:
    def __init__(self, threshold=0.7):
        self.threshold = threshold
        self.validated_data = []
    
    def validate(self, processed_data):
        """Validate processed data items"""
        for item in processed_data:
            try:
                validation_result = self._validate_item(item)
                
                if validation_result['score'] >= self.threshold:
                    validated_item = {
                        **item,
                        'validation': validation_result
                    }
                    
                    self.validated_data.append(validated_item)
                    self._save_validated_data(validated_item)
                else:
                    logger.warning(f"Item failed validation: {validation_result['reasons']}")
            except Exception as e:
                logger.error(f"Error validating data: {str(e)}")
    
    def _validate_item(self, item):
        """Validate a single data item"""
        score = 0.0
        reasons = []
        
        # Check content presence
        if 'content' in item and item['content']:
            score += 0.3
        else:
            reasons.append("Missing content")
        
        # Check metadata
        if 'metadata' in item and item['metadata']:
            score += 0.2
            
            # Check source URL
            if 'source_url' in item['metadata'] and item['metadata']['source_url']:
                score += 0.1
            else:
                reasons.append("Missing source URL")
                
            # Check domain
            if 'domain' in item['metadata'] and item['metadata']['domain']:
                score += 0.1
            else:
                reasons.append("Missing domain")
        else:
            reasons.append("Missing metadata")
        
        # Check processing information
        if 'processing' in item and item['processing']:
            score += 0.1
        else:
            reasons.append("Missing processing information")
        
        # Content-specific validation
        if item['metadata'].get('content_type') == 'text/html':
            # Check for minimum content length
            if len(str(item['content'].get('text', ''))) > 500:
                score += 0.1
            else:
                reasons.append("Content too short")
                
            # Check for paragraph extraction
            if len(item['content'].get('paragraphs', [])) > 3:
                score += 0.1
            else:
                reasons.append("Too few paragraphs extracted")
        
        elif item['metadata'].get('content_type') == 'application/json':
            # Check for non-empty JSON
            if item['content'] and (isinstance(item['content'], dict) or isinstance(item['content'], list)):
                score += 0.2
            else:
                reasons.append("Empty or invalid JSON")
        
        return {
            'score': score,
            'threshold': self.threshold,
            'passed': score >= self.threshold,
            'reasons': reasons
        }
    
    def _save_validated_data(self, validated_item):
        """Save validated data to file system"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        domain = validated_item['metadata']['domain']
        content_hash = hashlib.md5(str(validated_item).encode()).hexdigest()[:10]
        
        filename = f"{domain}_{timestamp}_{content_hash}.json"
        filepath = f"/home/ubuntu/nexus_project/data_gathering/validated/{filename}"
        
        try:
            with open(filepath, 'w') as f:
                json.dump(validated_item, f, indent=2)
            
            logger.info(f"Saved validated data to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving validated data: {str(e)}")
            return None

# Orchestrator
class DataGatheringOrchestrator:
    def __init__(self, config):
        self.config = config
        self.data_queue = Queue()
        self.gatherers = []
        self.processor = DataProcessor(self.data_queue)
        self.validator = DataValidator(config['validation_threshold'])
    
    def run(self):
        """Run the data gathering process"""
        logger.info("Starting data gathering orchestration")
        
        # Create gatherers for each domain and source
        self._create_gatherers()
        
        # Run gatherers in parallel
        self._run_gatherers()
        
        # Process gathered data
        logger.info("Processing gathered data")
        self.processor.process()
        
        # Validate processed data
        logger.info("Validating processed data")
        self.validator.validate(self.processor.processed_data)
        
        # Generate report
        self._generate_report()
        
        logger.info("Data gathering completed")
    
    def _create_gatherers(self):
        """Create data gatherers for each domain and source"""
        for domain, domain_config in self.config['domains'].items():
            for source in domain_config['sources']:
                if source['type'] == 'web':
                    gatherer = WebScraper(domain, source)
                elif source['type'] == 'api':
                    gatherer = ApiGatherer(domain, source)
                else:
                    logger.warning(f"Unknown source type: {source['type']}")
                    continue
                
                self.gatherers.append(gatherer)
    
    def _run_gatherers(self):
        """Run gatherers in parallel with thread pool"""
        threads = []
        max_threads = min(len(self.gatherers), self.config['max_threads'])
        
        logger.info(f"Running {len(self.gatherers)} gatherers with {max_threads} threads")
        
        # Sort gatherers by domain priority
        self.gatherers.sort(key=lambda g: self.config['domains'][g.domain]['priority'])
        
        # Create and start threads
        for gatherer in self.gatherers:
            while len(threads) >= max_threads:
                # Wait for a thread to complete
                for t in threads[:]:
                    if not t.is_alive():
                        threads.remove(t)
                
                if len(threads) >= max_threads:
                    time.sleep(0.1)
            
            # Start new thread
            thread = Thread(target=self._run_gatherer, args=(gatherer,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
    
    def _run_gatherer(self, gatherer):
        """Run a single gatherer"""
        try:
            success = gatherer.gather()
            if success:
                logger.info(f"Successfully gathered data from {gatherer.__class__.__name__} for {gatherer.domain}")
            else:
                logger.warning(f"Failed to gather data from {gatherer.__class__.__name__} for {gatherer.domain}")
        except Exception as e:
            logger.error(f"Error running gatherer {gatherer.__class__.__name__}: {str(e)}")
    
    def _generate_report(self):
        """Generate a report of the data gathering process"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'domains_processed': len(self.config['domains']),
            'sources_processed': len(self.gatherers),
            'items_gathered': self.data_queue.qsize(),
            'items_processed': len(self.processor.processed_data),
            'items_validated': len(self.validator.validated_data),
            'validation_rate': len(self.validator.validated_data) / len(self.processor.processed_data) if self.processor.processed_data else 0,
            'domain_stats': {}
        }
        
        # Gather domain-specific stats
        for domain in self.config['domains']:
            validated_domain_items = [item for item in self.validator.validated_data 
                                     if item['metadata']['domain'] == domain]
            
            report['domain_stats'][domain] = {
                'priority': self.config['domains'][domain]['priority'],
                'sources': len(self.config['domains'][domain]['sources']),
                'validated_items': len(validated_domain_items)
            }
        
        # Save report
        report_path = f"/home/ubuntu/nexus_project/data_gathering/data_gathering_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Generated report at {report_path}")
        
        # Print summary
        print("\n=== Data Gathering Summary ===")
        print(f"Domains processed: {report['domains_processed']}")
        print(f"Sources processed: {report['sources_processed']}")
        print(f"Items gathered: {report['items_gathered']}")
        print(f"Items processed: {report['items_processed']}")
        print(f"Items validated: {report['items_validated']}")
        print(f"Validation rate: {report['validation_rate']:.2f}")
        print(f"Report saved to: {report_path}")
        print("=============================\n")

# Integration with Knowledge Base
class KnowledgeBaseIntegrator:
    def __init__(self, validated_data):
        self.validated_data = validated_data
        self.knowledge_units = []
    
    def integrate(self):
        """Integrate validated data into knowledge base"""
        logger.info(f"Integrating {len(self.validated_data)} validated items into knowledge base")
        
        for item in self.validated_data:
            try:
                knowledge_unit = self._create_knowledge_unit(item)
                if knowledge_unit:
                    self.knowledge_units.append(knowledge_unit)
            except Exception as e:
                logger.error(f"Error creating knowledge unit: {str(e)}")
        
        logger.info(f"Created {len(self.knowledge_units)} knowledge units")
        
        # Save knowledge units
        self._save_knowledge_units()
        
        return self.knowledge_units
    
    def _create_knowledge_unit(self, item):
        """Create a knowledge unit from a validated data item"""
        domain = item['metadata']['domain']
        content_type = item['metadata'].get('content_type')
        
        # Extract content based on type
        if content_type == 'text/html':
            content = item['content'].get('text', '')
            summary = item['content'].get('summary', '')
            paragraphs = item['content'].get('paragraphs', [])
            
            # Create knowledge unit
            knowledge_unit = {
                'id': hashlib.md5(str(item).encode()).hexdigest(),
                'type': 'text',
                'domain': domain,
                'source': item['metadata'].get('source_url'),
                'timestamp': datetime.now().isoformat(),
                'content': content,
                'summary': summary,
                'segments': paragraphs,
                'metadata': {
                    'validation_score': item['validation']['score'],
                    'content_type': content_type,
                    'processing_timestamp': item['processing']['timestamp']
                },
                'tags': self._extract_tags(content, domain)
            }
            
            return knowledge_unit
            
        elif content_type == 'application/json':
            # For JSON, we need to extract relevant fields
            # This is a simplified example
            knowledge_unit = {
                'id': hashlib.md5(str(item).encode()).hexdigest(),
                'type': 'structured',
                'domain': domain,
                'source': item['metadata'].get('source_url'),
                'timestamp': datetime.now().isoformat(),
                'content': item['content'],
                'summary': str(item['content'])[:200] + '...' if len(str(item['content'])) > 200 else str(item['content']),
                'metadata': {
                    'validation_score': item['validation']['score'],
                    'content_type': content_type,
                    'processing_timestamp': item['processing']['timestamp'],
                    'structure': item['processing'].get('structure', {})
                },
                'tags': self._extract_tags(str(item['content']), domain)
            }
            
            return knowledge_unit
        
        else:
            logger.warning(f"Unsupported content type for knowledge unit: {content_type}")
            return None
    
    def _extract_tags(self, content, domain):
        """Extract relevant tags from content"""
        # This is a simplified tag extraction
        # In a real implementation, this would use NLP for topic extraction
        
        domain_tags = {
            'security': ['security', 'privacy', 'encryption', 'authentication', 'authorization', 
                        'vulnerability', 'threat', 'risk', 'compliance', 'protection'],
            'ai_ethics': ['ethics', 'fairness', 'bias', 'transparency', 'accountability', 
                         'responsibility', 'privacy', 'human rights', 'governance', 'regulation'],
            'computer_science': ['algorithm', 'data structure', 'programming', 'software', 'hardware', 
                               'database', 'network', 'architecture', 'computation', 'complexity'],
            'critical_thinking': ['logic', 'reasoning', 'fallacy', 'argument', 'evidence', 
                                'analysis', 'evaluation', 'inference', 'interpretation', 'explanation']
        }
        
        content_lower = content.lower()
        tags = []
        
        # Check for domain-specific tags
        for tag in domain_tags.get(domain, []):
            if tag.lower() in content_lower:
                tags.append(tag)
        
        # Add domain as a tag
        tags.append(domain)
        
        return tags
    
    def _save_knowledge_units(self):
        """Save knowledge units to file system"""
        if not self.knowledge_units:
            return
            
        # Create directory if it doesn't exist
        os.makedirs('/home/ubuntu/nexus_project/knowledge_base/units', exist_ok=True)
        
        # Save each knowledge unit
        for unit in self.knowledge_units:
            unit_id = unit['id']
            filepath = f"/home/ubuntu/nexus_project/knowledge_base/units/{unit_id}.json"
            
            try:
                with open(filepath, 'w') as f:
                    json.dump(unit, f, indent=2)
                
                logger.info(f"Saved knowledge unit to {filepath}")
            except Exception as e:
                logger.error(f"Error saving knowledge unit: {str(e)}")
        
        # Save index
        index = {
            'timestamp': datetime.now().isoformat(),
            'total_units': len(self.knowledge_units),
            'units': [{'id': unit['id'], 'domain': unit['domain'], 'type': unit['type']} 
                     for unit in self.knowledge_units]
        }
        
        index_path = f"/home/ubuntu/nexus_project/knowledge_base/index_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(index_path, 'w') as f:
                json.dump(index, f, indent=2)
            
            logger.info(f"Saved knowledge unit index to {index_path}")
        except Exception as e:
            logger.error(f"Error saving knowledge unit index: {str(e)}")

# Integration with Experiential Learning
class ExperientialDataGenerator:
    def __init__(self, knowledge_units):
        self.knowledge_units = knowledge_units
        self.experiences = []
    
    def generate_experiences(self):
        """Generate experiential data from knowledge units"""
        logger.info(f"Generating experiences from {len(self.knowledge_units)} knowledge units")
        
        for unit in self.knowledge_units:
            try:
                experiences = self._generate_from_unit(unit)
                if experiences:
                    self.experiences.extend(experiences)
            except Exception as e:
                logger.error(f"Error generating experiences: {str(e)}")
        
        logger.info(f"Generated {len(self.experiences)} experiences")
        
        # Save experiences
        self._save_experiences()
        
        return self.experiences
    
    def _generate_from_unit(self, unit):
        """Generate experiences from a single knowledge unit"""
        domain = unit['domain']
        unit_type = unit['type']
        experiences = []
        
        if unit_type == 'text':
            # Generate scenarios from text content
            if domain == 'security':
                experiences.append(self._generate_security_scenario(unit))
            elif domain == 'ai_ethics':
                experiences.append(self._generate_ethics_scenario(unit))
            elif domain == 'critical_thinking':
                experiences.append(self._generate_reasoning_scenario(unit))
        
        elif unit_type == 'structured':
            # Generate scenarios from structured content
            if domain == 'computer_science':
                experiences.append(self._generate_problem_solving_scenario(unit))
        
        return [exp for exp in experiences if exp]  # Filter out None values
    
    def _generate_security_scenario(self, unit):
        """Generate a security-related scenario"""
        # This is a simplified example
        return {
            'id': f"exp_{hashlib.md5(unit['id'].encode()).hexdigest()}",
            'domain': 'security',
            'scenario_type': 'security_assessment',
            'description': f"Security assessment scenario based on {unit['source']}",
            'content': {
                'situation': unit['summary'],
                'assets': ['data', 'systems', 'network'],
                'threats': ['unauthorized access', 'data breach', 'malware'],
                'questions': [
                    'What are the main security vulnerabilities?',
                    'What controls would mitigate these risks?',
                    'How would you prioritize security measures?'
                ]
            },
            'source_unit': unit['id'],
            'tags': unit['tags']
        }
    
    def _generate_ethics_scenario(self, unit):
        """Generate an ethics-related scenario"""
        return {
            'id': f"exp_{hashlib.md5(unit['id'].encode()).hexdigest()}",
            'domain': 'ethics',
            'scenario_type': 'ethical_dilemma',
            'description': f"Ethical dilemma scenario based on {unit['source']}",
            'content': {
                'situation': unit['summary'],
                'stakeholders': ['users', 'developers', 'society'],
                'values_at_stake': ['privacy', 'fairness', 'transparency'],
                'options': [
                    {'description': 'Prioritize user privacy', 'consequences': 'Limited functionality'},
                    {'description': 'Maximize functionality', 'consequences': 'Reduced privacy'}
                ],
                'questions': [
                    'What values are in conflict?',
                    'How would you balance these competing interests?',
                    'What principles should guide this decision?'
                ]
            },
            'source_unit': unit['id'],
            'tags': unit['tags']
        }
    
    def _generate_reasoning_scenario(self, unit):
        """Generate a critical thinking scenario"""
        return {
            'id': f"exp_{hashlib.md5(unit['id'].encode()).hexdigest()}",
            'domain': 'critical_thinking',
            'scenario_type': 'argument_analysis',
            'description': f"Argument analysis scenario based on {unit['source']}",
            'content': {
                'argument': unit['summary'],
                'components': ['premises', 'conclusion', 'assumptions'],
                'potential_fallacies': ['appeal to authority', 'false dichotomy', 'hasty generalization'],
                'questions': [
                    'What are the main claims being made?',
                    'What evidence supports these claims?',
                    'Are there logical fallacies present?'
                ]
            },
            'source_unit': unit['id'],
            'tags': unit['tags']
        }
    
    def _generate_problem_solving_scenario(self, unit):
        """Generate a problem-solving scenario"""
        return {
            'id': f"exp_{hashlib.md5(unit['id'].encode()).hexdigest()}",
            'domain': 'problem_solving',
            'scenario_type': 'algorithm_challenge',
            'description': f"Algorithm challenge based on {unit['source']}",
            'content': {
                'problem': f"Implement a solution based on concepts from {unit['summary']}",
                'constraints': ['time efficiency', 'space efficiency', 'readability'],
                'test_cases': [
                    {'input': 'example_input_1', 'expected_output': 'example_output_1'},
                    {'input': 'example_input_2', 'expected_output': 'example_output_2'}
                ],
                'hints': [
                    'Consider using appropriate data structures',
                    'Think about edge cases',
                    'Optimize for the most common operations'
                ]
            },
            'source_unit': unit['id'],
            'tags': unit['tags']
        }
    
    def _save_experiences(self):
        """Save generated experiences to file system"""
        if not self.experiences:
            return
            
        # Create directory if it doesn't exist
        os.makedirs('/home/ubuntu/nexus_project/experiential_learning/scenarios', exist_ok=True)
        
        # Save each experience
        for exp in self.experiences:
            exp_id = exp['id']
            filepath = f"/home/ubuntu/nexus_project/experiential_learning/scenarios/{exp_id}.json"
            
            try:
                with open(filepath, 'w') as f:
                    json.dump(exp, f, indent=2)
                
                logger.info(f"Saved experience to {filepath}")
            except Exception as e:
                logger.error(f"Error saving experience: {str(e)}")
        
        # Save index
        index = {
            'timestamp': datetime.now().isoformat(),
            'total_experiences': len(self.experiences),
            'experiences': [{'id': exp['id'], 'domain': exp['domain'], 'type': exp['scenario_type']} 
                           for exp in self.experiences]
        }
        
        index_path = f"/home/ubuntu/nexus_project/experiential_learning/index_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(index_path, 'w') as f:
                json.dump(index, f, indent=2)
            
            logger.info(f"Saved experience index to {index_path}")
        except Exception as e:
            logger.error(f"Error saving experience index: {str(e)}")

# Main execution
def main():
    print("=== Kali Ka Automated Data Gathering System ===")
    print("Starting data gathering process...")
    
    # Create orchestrator
    orchestrator = DataGatheringOrchestrator(CONFIG)
    
    # Run data gathering
    orchestrator.run()
    
    # Integrate with knowledge base
    integrator = KnowledgeBaseIntegrator(orchestrator.validator.validated_data)
    knowledge_units = integrator.integrate()
    
    # Generate experiential data
    exp_generator = ExperientialDataGenerator(knowledge_units)
    experiences = exp_generator.generate_experiences()
    
    print("\n=== Data Gathering Complete ===")
    print(f"Knowledge units created: {len(knowledge_units)}")
    print(f"Experiences generated: {len(experiences)}")
    print("===============================\n")

if __name__ == "__main__":
    main()
