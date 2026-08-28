"""
Truth Validation Engine for Symbol Lexicon System
Multi-source verification with GPU acceleration for JSON lexicon slots

Validates lexicon entries with format:
{
  "binary": "10001011001101100000000000000001000101",
  "hex": "8b6800010", 
  "font_symbol": "CJKM_001100100",
  "tone_signature": "TONE_1134",
  "status": "AVAILABLE"
}
"""

import json
import re
import hashlib
import asyncio
import aiohttp
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
from collections import defaultdict
import time
from concurrent.futures import ThreadPoolExecutor
import requests

@dataclass
class ValidationResult:
    """Result of truth validation for a lexicon slot"""
    slot_id: str
    is_valid: bool
    confidence_score: float
    validation_sources: List[str]
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]

@dataclass
class LexiconSlot:
    """Lexicon slot structure matching user's format"""
    binary: str
    hex: str
    font_symbol: str
    tone_signature: str
    status: str
    
    def __post_init__(self):
        """Validate basic structure"""
        if not all([self.binary, self.hex, self.font_symbol, self.tone_signature, self.status]):
            raise ValueError("All lexicon slot fields must be non-empty")

class TruthEngine:
    """
    Multi-source truth validation engine for lexicon slots
    
    Validation Pipeline:
    1. Structural validation (format, consistency)
    2. Binary/hex cross-validation
    3. Font symbol verification
    4. Tone signature analysis
    5. External source verification
    6. Confidence scoring
    """
    
    def __init__(self, gpu_manager=None):
        self.gpu_manager = gpu_manager
        self.validation_sources = self._initialize_sources()
        self.cache = {}
        self.batch_size = 1000
        self.confidence_thresholds = {
            "auto_approve": 0.95,
            "human_review": 0.85,
            "reject": 0.50
        }
        
    def _initialize_sources(self) -> Dict[str, Dict[str, Any]]:
        """Initialize validation sources"""
        return {
            "structural": {
                "name": "Structural Validation",
                "weight": 0.3,
                "enabled": True
            },
            "cross_validation": {
                "name": "Binary/Hex Cross-Validation", 
                "weight": 0.25,
                "enabled": True
            },
            "font_verification": {
                "name": "Font Symbol Verification",
                "weight": 0.2,
                "enabled": True
            },
            "tone_analysis": {
                "name": "Tone Signature Analysis",
                "weight": 0.15,
                "enabled": True
            },
            "external_apis": {
                "name": "External API Verification",
                "weight": 0.1,
                "enabled": False  # Disabled by default for privacy
            }
        }
    
    def validate_slot(self, slot_data: Dict[str, str], slot_id: str = None) -> ValidationResult:
        """Validate a single lexicon slot"""
        if not slot_id:
            slot_id = self._generate_slot_id(slot_data)
        
        # Check cache first
        cache_key = self._get_cache_key(slot_data)
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # Parse slot
            slot = LexiconSlot(**slot_data)
            
            # Run validation pipeline
            validation_results = []
            errors = []
            warnings = []
            
            # 1. Structural validation
            if self.validation_sources["structural"]["enabled"]:
                result = self._validate_structure(slot)
                validation_results.append(("structural", result))
                if not result["valid"]:
                    errors.extend(result.get("errors", []))
                warnings.extend(result.get("warnings", []))
            
            # 2. Binary/hex cross-validation
            if self.validation_sources["cross_validation"]["enabled"]:
                result = self._validate_binary_hex_consistency(slot)
                validation_results.append(("cross_validation", result))
                if not result["valid"]:
                    errors.extend(result.get("errors", []))
                warnings.extend(result.get("warnings", []))
            
            # 3. Font symbol verification
            if self.validation_sources["font_verification"]["enabled"]:
                result = self._validate_font_symbol(slot)
                validation_results.append(("font_verification", result))
                if not result["valid"]:
                    errors.extend(result.get("errors", []))
                warnings.extend(result.get("warnings", []))
            
            # 4. Tone signature analysis
            if self.validation_sources["tone_analysis"]["enabled"]:
                result = self._validate_tone_signature(slot)
                validation_results.append(("tone_analysis", result))
                if not result["valid"]:
                    errors.extend(result.get("errors", []))
                warnings.extend(result.get("warnings", []))
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(validation_results)
            
            # Determine overall validity
            is_valid = confidence_score >= self.confidence_thresholds["reject"]
            
            # Create result
            result = ValidationResult(
                slot_id=slot_id,
                is_valid=is_valid,
                confidence_score=confidence_score,
                validation_sources=[source for source, _ in validation_results],
                errors=errors,
                warnings=warnings,
                metadata={
                    "validation_details": dict(validation_results),
                    "timestamp": time.time(),
                    "cache_key": cache_key
                }
            )
            
            # Cache result
            self.cache[cache_key] = result
            
            return result
            
        except Exception as e:
            # Handle validation errors gracefully
            return ValidationResult(
                slot_id=slot_id,
                is_valid=False,
                confidence_score=0.0,
                validation_sources=[],
                errors=[f"Validation exception: {str(e)}"],
                warnings=[],
                metadata={"exception": str(e)}
            )
    
    def _validate_structure(self, slot: LexiconSlot) -> Dict[str, Any]:
        """Validate basic structure and format"""
        errors = []
        warnings = []
        
        # Binary validation
        if not re.match(r'^[01]+$', slot.binary):
            errors.append("Binary field contains non-binary characters")
        
        # Hex validation
        if not re.match(r'^[0-9a-fA-F]+$', slot.hex):
            errors.append("Hex field contains non-hexadecimal characters")
        
        # Font symbol validation
        if not re.match(r'^[A-Z_0-9]+$', slot.font_symbol):
            warnings.append("Font symbol contains unexpected characters")
        
        # Tone signature validation
        if not re.match(r'^TONE_\d+$', slot.tone_signature):
            errors.append("Tone signature format invalid (expected TONE_XXXX)")
        
        # Status validation
        valid_statuses = {"AVAILABLE", "RESERVED", "DEPRECATED", "PENDING"}
        if slot.status not in valid_statuses:
            errors.append(f"Invalid status: {slot.status}")
        
        return {
            "valid": len(errors) == 0,
            "score": 1.0 if len(errors) == 0 else 0.0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_binary_hex_consistency(self, slot: LexiconSlot) -> Dict[str, Any]:
        """Validate that binary and hex representations are consistent"""
        errors = []
        warnings = []
        
        try:
            # Convert binary to hex
            binary_as_int = int(slot.binary, 2)
            binary_as_hex = hex(binary_as_int)[2:].upper()
            
            # Compare with provided hex
            provided_hex = slot.hex.upper()
            
            if binary_as_hex != provided_hex:
                errors.append(f"Binary/hex mismatch: binary converts to {binary_as_hex}, but hex is {provided_hex}")
            
            # Check for reasonable length
            if len(slot.binary) > 64:
                warnings.append("Binary representation is unusually long")
            
            if len(slot.hex) > 16:
                warnings.append("Hex representation is unusually long")
                
        except ValueError as e:
            errors.append(f"Binary/hex conversion error: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "score": 1.0 if len(errors) == 0 else 0.0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_font_symbol(self, slot: LexiconSlot) -> Dict[str, Any]:
        """Validate font symbol format and consistency"""
        errors = []
        warnings = []
        
        # Check font symbol format
        parts = slot.font_symbol.split('_')
        if len(parts) < 2:
            errors.append("Font symbol should contain at least one underscore")
        
        # Check prefix patterns
        valid_prefixes = {"CJKM", "LATIN", "CYRILLIC", "ARABIC", "SYMBOL", "MATH", "EMOJI"}
        if parts[0] not in valid_prefixes:
            warnings.append(f"Unusual font symbol prefix: {parts[0]}")
        
        # Check numeric suffix
        if len(parts) > 1 and not re.match(r'^\d+$', parts[-1]):
            warnings.append("Font symbol should end with numeric identifier")
        
        return {
            "valid": len(errors) == 0,
            "score": 1.0 if len(errors) == 0 else 0.5 if len(warnings) == 0 else 0.3,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_tone_signature(self, slot: LexiconSlot) -> Dict[str, Any]:
        """Validate tone signature format and range"""
        errors = []
        warnings = []
        
        # Extract tone number
        match = re.match(r'^TONE_(\d+)$', slot.tone_signature)
        if not match:
            errors.append("Invalid tone signature format")
            return {
                "valid": False,
                "score": 0.0,
                "errors": errors,
                "warnings": warnings
            }
        
        tone_number = int(match.group(1))
        
        # Check reasonable range
        if tone_number < 1 or tone_number > 10000:
            warnings.append(f"Tone number {tone_number} is outside typical range (1-10000)")
        
        # Check for common tone patterns
        if tone_number % 100 == 0:
            warnings.append("Tone number is a round hundred - verify intentional")
        
        return {
            "valid": len(errors) == 0,
            "score": 1.0 if len(errors) == 0 else 0.0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _calculate_confidence_score(self, validation_results: List[Tuple[str, Dict[str, Any]]]) -> float:
        """Calculate weighted confidence score"""
        total_weight = 0.0
        weighted_score = 0.0
        
        for source_name, result in validation_results:
            if source_name in self.validation_sources:
                weight = self.validation_sources[source_name]["weight"]
                score = result.get("score", 0.0)
                
                weighted_score += weight * score
                total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return weighted_score / total_weight
    
    def validate_batch(self, slots: List[Dict[str, Any]], 
                      use_gpu: bool = True) -> List[ValidationResult]:
        """Validate multiple slots with optional GPU acceleration"""
        if use_gpu and self.gpu_manager:
            return self._validate_batch_gpu(slots)
        else:
            return self._validate_batch_cpu(slots)
    
    def _validate_batch_cpu(self, slots: List[Dict[str, Any]]) -> List[ValidationResult]:
        """CPU-based batch validation"""
        results = []
        
        # Use thread pool for parallel processing
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for i, slot_data in enumerate(slots):
                future = executor.submit(self.validate_slot, slot_data, f"slot_{i}")
                futures.append(future)
            
            for future in futures:
                results.append(future.result())
        
        return results
    
    def _validate_batch_gpu(self, slots: List[Dict[str, Any]]) -> List[ValidationResult]:
        """GPU-accelerated batch validation"""
        # For now, fallback to CPU (GPU acceleration would require CUDA/ROCm kernels)
        print("🔥 GPU acceleration requested - using optimized CPU batch processing")
        return self._validate_batch_cpu(slots)
    
    def load_lexicon_file(self, filepath: str) -> List[Dict[str, Any]]:
        """Load lexicon slots from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # If it's a dict, extract values or look for a 'slots' key
            if 'slots' in data:
                return data['slots']
            else:
                return list(data.values())
        else:
            raise ValueError("Unsupported JSON structure")
    
    def validate_lexicon_file(self, filepath: str, output_path: str = None) -> Dict[str, Any]:
        """Validate entire lexicon file and generate report"""
        print(f"🔍 Loading lexicon file: {filepath}")
        slots = self.load_lexicon_file(filepath)
        
        print(f"📊 Validating {len(slots)} lexicon slots...")
        results = self.validate_batch(slots)
        
        # Generate statistics
        stats = self._generate_validation_stats(results)
        
        # Create report
        report = {
            "file_path": filepath,
            "total_slots": len(slots),
            "validation_results": [asdict(result) for result in results],
            "statistics": stats,
            "timestamp": time.time()
        }
        
        # Save report if output path provided
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"📝 Validation report saved to: {output_path}")
        
        return report
    
    def _generate_validation_stats(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Generate validation statistics"""
        total = len(results)
        valid = sum(1 for r in results if r.is_valid)
        
        confidence_distribution = defaultdict(int)
        error_types = defaultdict(int)
        
        for result in results:
            # Confidence distribution
            if result.confidence_score >= 0.95:
                confidence_distribution["excellent"] += 1
            elif result.confidence_score >= 0.85:
                confidence_distribution["good"] += 1
            elif result.confidence_score >= 0.70:
                confidence_distribution["fair"] += 1
            else:
                confidence_distribution["poor"] += 1
            
            # Error types
            for error in result.errors:
                error_types[error] += 1
        
        return {
            "total_slots": total,
            "valid_slots": valid,
            "invalid_slots": total - valid,
            "validity_rate": valid / total if total > 0 else 0,
            "average_confidence": sum(r.confidence_score for r in results) / total if total > 0 else 0,
            "confidence_distribution": dict(confidence_distribution),
            "common_errors": dict(sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:10])
        }
    
    def _generate_slot_id(self, slot_data: Dict[str, str]) -> str:
        """Generate unique ID for slot"""
        content = json.dumps(slot_data, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _get_cache_key(self, slot_data: Dict[str, str]) -> str:
        """Generate cache key for slot"""
        return self._generate_slot_id(slot_data)

def main():
    """Demo of Truth Engine capabilities"""
    print("🔍 Truth Engine Demo")
    print("=" * 50)
    
    # Initialize engine
    engine = TruthEngine()
    
    # Sample lexicon slots matching user's format
    sample_slots = [
        {
            "binary": "10001011001101100000000000000001000101",
            "hex": "8B6800010",
            "font_symbol": "CJKM_001100100",
            "tone_signature": "TONE_1134",
            "status": "AVAILABLE"
        },
        {
            "binary": "11000101110111111111111111111111100110",
            "hex": "C5DFFFFF6",
            "font_symbol": "LATIN_FF1E2",
            "tone_signature": "TONE_1670",
            "status": "AVAILABLE"
        },
        {
            "binary": "10110001100101000000000000000001100101",
            "hex": "B1940065",
            "font_symbol": "CJKM_001100100",
            "tone_signature": "TONE_3199",
            "status": "AVAILABLE"
        }
    ]
    
    # Validate individual slots
    print("\n🔍 Individual Slot Validation:")
    for i, slot_data in enumerate(sample_slots):
        result = engine.validate_slot(slot_data, f"demo_slot_{i}")
        print(f"\nSlot {i+1}:")
        print(f"  Valid: {result.is_valid}")
        print(f"  Confidence: {result.confidence_score:.3f}")
        if result.errors:
            print(f"  Errors: {result.errors}")
        if result.warnings:
            print(f"  Warnings: {result.warnings}")
    
    # Batch validation
    print(f"\n🚀 Batch Validation:")
    batch_results = engine.validate_batch(sample_slots)
    stats = engine._generate_validation_stats(batch_results)
    
    print(f"Total slots: {stats['total_slots']}")
    print(f"Valid slots: {stats['valid_slots']}")
    print(f"Validity rate: {stats['validity_rate']:.1%}")
    print(f"Average confidence: {stats['average_confidence']:.3f}")

if __name__ == "__main__":
    main()

