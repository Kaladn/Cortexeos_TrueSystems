"""
Error Handling Improvements for Automated Data Gathering System

This module enhances the error handling capabilities of the automated data gathering system,
providing more robust recovery mechanisms and detailed error reporting.

Author: Manus
Date: April 8, 2025
"""

import os
import json
import time
import traceback
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

class ErrorHandler:
    def __init__(self, log_dir="/home/ubuntu/nexus_project/data_gathering/logs"):
        self.log_dir = log_dir
        self.error_log_file = f"{log_dir}/error_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.errors = []
        self.retry_counts = {}
        
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Initialize error log
        self._initialize_error_log()
    
    def _initialize_error_log(self):
        """Initialize the error log file"""
        with open(self.error_log_file, 'w') as f:
            json.dump({
                "start_time": datetime.now().isoformat(),
                "errors": []
            }, f, indent=2)
    
    def log_error(self, error_type: str, source: str, details: Dict[str, Any], exception: Optional[Exception] = None) -> Dict[str, Any]:
        """
        Log an error with detailed information
        
        Args:
            error_type: Type of error (e.g., 'http', 'parsing', 'validation')
            source: Source of the error (e.g., URL, file path)
            details: Additional error details
            exception: Exception object if available
            
        Returns:
            Error record with unique ID
        """
        error_id = f"err_{len(self.errors) + 1}_{int(time.time())}"
        
        error_record = {
            "id": error_id,
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "source": source,
            "details": details,
            "recoverable": self._is_recoverable(error_type, details),
            "retry_count": self.retry_counts.get(source, 0),
            "stack_trace": traceback.format_exc() if exception else None,
            "exception_type": type(exception).__name__ if exception else None,
            "exception_message": str(exception) if exception else None
        }
        
        self.errors.append(error_record)
        
        # Update error log file
        try:
            with open(self.error_log_file, 'r') as f:
                log_data = json.load(f)
            
            log_data["errors"].append(error_record)
            log_data["last_updated"] = datetime.now().isoformat()
            log_data["total_errors"] = len(log_data["errors"])
            
            with open(self.error_log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
        except Exception as e:
            print(f"Failed to update error log: {str(e)}")
        
        return error_record
    
    def _is_recoverable(self, error_type: str, details: Dict[str, Any]) -> bool:
        """Determine if an error is potentially recoverable"""
        if error_type == 'http':
            # HTTP errors that might be temporary
            status_code = details.get('status_code', 0)
            return status_code in [429, 500, 502, 503, 504]
        
        elif error_type == 'connection':
            # Connection errors are often temporary
            return True
        
        elif error_type == 'timeout':
            # Timeout errors might be resolved with retry
            return True
        
        # Default to non-recoverable for other error types
        return False
    
    def should_retry(self, source: str, max_retries: int = 3) -> bool:
        """
        Determine if a failed operation should be retried
        
        Args:
            source: Source identifier (e.g., URL)
            max_retries: Maximum number of retry attempts
            
        Returns:
            Boolean indicating whether to retry
        """
        # Get current retry count
        current_retries = self.retry_counts.get(source, 0)
        
        # Check if we've exceeded max retries
        if current_retries >= max_retries:
            return False
        
        # Find the most recent error for this source
        source_errors = [e for e in self.errors if e['source'] == source]
        if not source_errors:
            return True
        
        latest_error = source_errors[-1]
        
        # Only retry recoverable errors
        if not latest_error['recoverable']:
            return False
        
        # Increment retry count
        self.retry_counts[source] = current_retries + 1
        
        return True
    
    def get_retry_delay(self, retry_count: int) -> float:
        """
        Calculate exponential backoff delay for retries
        
        Args:
            retry_count: Current retry attempt number
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff with jitter
        base_delay = min(30, 2 ** retry_count)
        jitter = random.uniform(0, 0.1 * base_delay)
        return base_delay + jitter
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of all errors"""
        error_types = {}
        recoverable_count = 0
        
        for error in self.errors:
            error_type = error['type']
            error_types[error_type] = error_types.get(error_type, 0) + 1
            
            if error['recoverable']:
                recoverable_count += 1
        
        return {
            "total_errors": len(self.errors),
            "error_types": error_types,
            "recoverable_errors": recoverable_count,
            "non_recoverable_errors": len(self.errors) - recoverable_count,
            "unique_sources": len(set(error['source'] for error in self.errors))
        }
    
    def get_errors_by_type(self, error_type: str) -> List[Dict[str, Any]]:
        """Get all errors of a specific type"""
        return [e for e in self.errors if e['type'] == error_type]

# HTTP Request Handler with improved error handling
class HttpRequestHandler:
    def __init__(self, error_handler: ErrorHandler, config: Dict[str, Any]):
        self.error_handler = error_handler
        self.config = config
        self.domain_timestamps = {}
    
    def fetch_url(self, url: str, domain: str, headers: Optional[Dict[str, str]] = None) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Fetch content from a URL with robust error handling
        
        Args:
            url: URL to fetch
            domain: Domain category for the URL
            headers: Optional HTTP headers
            
        Returns:
            Tuple of (success, content, error_info)
        """
        # Respect rate limits
        self._respect_rate_limits(urllib.parse.urlparse(url).netloc)
        
        # Set default headers if none provided
        if headers is None:
            headers = {'User-Agent': self.config['user_agent']}
        
        # Try to fetch the URL
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read().decode('utf-8')
                return True, content, None
                
        except urllib.error.HTTPError as e:
            # Handle HTTP errors
            error_details = {
                'status_code': e.code,
                'reason': e.reason,
                'headers': dict(e.headers)
            }
            
            error_record = self.error_handler.log_error(
                error_type='http',
                source=url,
                details=error_details,
                exception=e
            )
            
            return False, None, error_record
            
        except urllib.error.URLError as e:
            # Handle connection errors
            error_details = {
                'reason': str(e.reason)
            }
            
            error_record = self.error_handler.log_error(
                error_type='connection',
                source=url,
                details=error_details,
                exception=e
            )
            
            return False, None, error_record
            
        except TimeoutError:
            # Handle timeout errors
            error_details = {
                'timeout': 30
            }
            
            error_record = self.error_handler.log_error(
                error_type='timeout',
                source=url,
                details=error_details
            )
            
            return False, None, error_record
            
        except Exception as e:
            # Handle other errors
            error_details = {
                'exception_type': type(e).__name__
            }
            
            error_record = self.error_handler.log_error(
                error_type='unknown',
                source=url,
                details=error_details,
                exception=e
            )
            
            return False, None, error_record
    
    def _respect_rate_limits(self, domain: str):
        """Ensure we don't overwhelm sources with requests"""
        current_time = time.time()
        if domain in self.domain_timestamps:
            elapsed = current_time - self.domain_timestamps[domain]
            if elapsed < self.config['request_delay']:
                time.sleep(self.config['request_delay'] - elapsed)
        
        self.domain_timestamps[domain] = time.time()

# Import for random jitter in retry delay
import random
