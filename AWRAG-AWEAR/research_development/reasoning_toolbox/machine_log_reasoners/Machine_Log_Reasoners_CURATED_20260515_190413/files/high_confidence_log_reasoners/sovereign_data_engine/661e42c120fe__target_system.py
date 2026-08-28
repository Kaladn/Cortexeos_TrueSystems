"""
Target System Module
Handles intelligent targeting for massive genomic datasets
Pre-programmed target areas and pattern following
"""

import re
import json
from typing import Dict, Any, List, Tuple, Optional, Set
from collections import defaultdict
from dataclasses import dataclass

@dataclass
class TargetRegion:
    """Represents a target region in genomic data"""
    name: str
    pattern: str
    region_type: str  # 'gene', 'promoter', 'enhancer', 'motif', 'repeat', 'custom'
    priority: int
    context_left: int
    context_right: int
    description: str = ""

@dataclass
class TargetHit:
    """Represents a found target in the data"""
    region: TargetRegion
    position: int
    sequence: str
    confidence: float
    context_left: str
    context_right: str

class TargetSystem:
    """Intelligent targeting system for genomic analysis"""
    
    def __init__(self):
        self.target_regions = {}
        self.target_patterns = {}
        self.load_default_targets()
    
    def load_default_targets(self):
        """Load pre-programmed genomic target areas"""
        
        # Common genomic motifs and regulatory elements
        default_targets = [
            TargetRegion(
                name="TATA_box",
                pattern="TATAAA[ATGC]{0,3}",
                region_type="promoter",
                priority=9,
                context_left=50,
                context_right=50,
                description="TATA box promoter element"
            ),
            TargetRegion(
                name="start_codon",
                pattern="ATG",
                region_type="gene",
                priority=10,
                context_left=20,
                context_right=100,
                description="Translation start site"
            ),
            TargetRegion(
                name="stop_codon",
                pattern="(TAA|TAG|TGA)",
                region_type="gene",
                priority=8,
                context_left=100,
                context_right=20,
                description="Translation stop site"
            ),
            TargetRegion(
                name="splice_donor",
                pattern="GT[ATGC]{2,20}AG",
                region_type="gene",
                priority=7,
                context_left=30,
                context_right=30,
                description="Splice site donor-acceptor"
            ),
            TargetRegion(
                name="CpG_island",
                pattern="(CG){3,}",
                region_type="enhancer",
                priority=6,
                context_left=100,
                context_right=100,
                description="CpG methylation site"
            ),
            TargetRegion(
                name="poly_A_signal",
                pattern="AATAAA",
                region_type="gene",
                priority=5,
                context_left=50,
                context_right=30,
                description="Polyadenylation signal"
            ),
            TargetRegion(
                name="ribosome_binding",
                pattern="AGGAGG",
                region_type="gene",
                priority=8,
                context_left=20,
                context_right=10,
                description="Ribosome binding site (Shine-Dalgarno)"
            ),
            TargetRegion(
                name="CAAT_box",
                pattern="CCAAT",
                region_type="promoter",
                priority=6,
                context_left=40,
                context_right=40,
                description="CAAT box promoter element"
            ),
            TargetRegion(
                name="GC_box",
                pattern="GGGCGG",
                region_type="promoter",
                priority=6,
                context_left=40,
                context_right=40,
                description="GC box promoter element"
            ),
            TargetRegion(
                name="tandem_repeat",
                pattern="([ATGC]{2,10})\\1{2,}",
                region_type="repeat",
                priority=4,
                context_left=50,
                context_right=50,
                description="Tandem repeat sequences"
            )
        ]
        
        for target in default_targets:
            self.target_regions[target.name] = target
    
    def add_custom_target(self, name: str, pattern: str, region_type: str, 
                         priority: int, context_left: int, context_right: int,
                         description: str = ""):
        """Add custom target region"""
        target = TargetRegion(
            name=name,
            pattern=pattern,
            region_type=region_type,
            priority=priority,
            context_left=context_left,
            context_right=context_right,
            description=description
        )
        self.target_regions[name] = target
    
    def scan_for_targets(self, data: str, target_types: List[str] = None, 
                        max_hits: int = 1000) -> List[TargetHit]:
        """
        Scan data for target regions
        
        Args:
            data: Genomic sequence data
            target_types: List of target types to search for
            max_hits: Maximum number of hits to return
            
        Returns:
            List of target hits sorted by priority and position
        """
        if target_types is None:
            target_types = list(self.target_regions.keys())
        
        all_hits = []
        
        for target_name in target_types:
            if target_name not in self.target_regions:
                continue
                
            target = self.target_regions[target_name]
            hits = self._find_pattern_matches(data, target)
            all_hits.extend(hits)
        
        # Sort by priority (descending) then by position
        all_hits.sort(key=lambda x: (-x.region.priority, x.position))
        
        return all_hits[:max_hits]
    
    def _find_pattern_matches(self, data: str, target: TargetRegion) -> List[TargetHit]:
        """Find all matches for a specific target pattern"""
        hits = []
        
        try:
            pattern = re.compile(target.pattern, re.IGNORECASE)
            
            for match in pattern.finditer(data):
                start_pos = match.start()
                end_pos = match.end()
                matched_sequence = match.group()
                
                # Extract context
                context_start = max(0, start_pos - target.context_left)
                context_end = min(len(data), end_pos + target.context_right)
                
                context_left = data[context_start:start_pos]
                context_right = data[end_pos:context_end]
                
                # Calculate confidence based on pattern specificity
                confidence = self._calculate_confidence(matched_sequence, target)
                
                hit = TargetHit(
                    region=target,
                    position=start_pos,
                    sequence=matched_sequence,
                    confidence=confidence,
                    context_left=context_left,
                    context_right=context_right
                )
                
                hits.append(hit)
                
        except re.error as e:
            print(f"Invalid regex pattern for {target.name}: {e}")
        
        return hits
    
    def _calculate_confidence(self, sequence: str, target: TargetRegion) -> float:
        """Calculate confidence score for a target match"""
        base_confidence = 0.5
        
        # Adjust based on sequence length vs pattern complexity
        if len(sequence) >= 6:
            base_confidence += 0.2
        
        # Adjust based on target type priority
        priority_bonus = target.priority / 10.0 * 0.3
        base_confidence += priority_bonus
        
        # Adjust based on pattern specificity
        if target.region_type in ['gene', 'promoter']:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def follow_target_pattern(self, data: str, initial_hit: TargetHit, 
                             follow_distance: int = 1000) -> List[TargetHit]:
        """
        Follow a target pattern to find related targets nearby
        
        Args:
            data: Genomic sequence data
            initial_hit: Starting target hit
            follow_distance: Distance to search around initial hit
            
        Returns:
            List of related target hits
        """
        start_search = max(0, initial_hit.position - follow_distance)
        end_search = min(len(data), initial_hit.position + follow_distance)
        
        search_region = data[start_search:end_search]
        
        # Find related targets based on region type
        related_types = self._get_related_target_types(initial_hit.region.region_type)
        
        related_hits = []
        for target_name in related_types:
            if target_name in self.target_regions:
                target = self.target_regions[target_name]
                hits = self._find_pattern_matches(search_region, target)
                
                # Adjust positions to global coordinates
                for hit in hits:
                    hit.position += start_search
                    related_hits.append(hit)
        
        return related_hits
    
    def _get_related_target_types(self, region_type: str) -> List[str]:
        """Get related target types for pattern following"""
        relationships = {
            'promoter': ['start_codon', 'TATA_box', 'CAAT_box', 'GC_box'],
            'gene': ['start_codon', 'stop_codon', 'splice_donor', 'poly_A_signal'],
            'enhancer': ['CpG_island', 'TATA_box'],
            'repeat': ['tandem_repeat'],
            'motif': ['CpG_island', 'TATA_box']
        }
        
        return relationships.get(region_type, [])
    
    def create_target_cascade_config(self, hits: List[TargetHit], 
                                   base_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create cascade configurations based on target hits
        
        Args:
            hits: List of target hits
            base_config: Base configuration template
            
        Returns:
            List of configurations for each target
        """
        configs = []
        
        for hit in hits:
            config = base_config.copy()
            
            # Adjust N-1-N parameters based on target type
            if hit.region.region_type == 'gene':
                config['left_width'] = max(config.get('left_width', 10), 20)
                config['right_width'] = max(config.get('right_width', 10), 50)
                config['anchor_width'] = len(hit.sequence)
            elif hit.region.region_type == 'promoter':
                config['left_width'] = max(config.get('left_width', 10), 50)
                config['right_width'] = max(config.get('right_width', 10), 30)
                config['anchor_width'] = len(hit.sequence)
            elif hit.region.region_type == 'enhancer':
                config['left_width'] = max(config.get('left_width', 10), 100)
                config['right_width'] = max(config.get('right_width', 10), 100)
                config['anchor_width'] = len(hit.sequence)
            
            # Add target-specific metadata
            config['target_hit'] = {
                'name': hit.region.name,
                'position': hit.position,
                'sequence': hit.sequence,
                'confidence': hit.confidence,
                'region_type': hit.region.region_type
            }
            
            configs.append(config)
        
        return configs
    
    def optimize_for_massive_datasets(self, data_size: int) -> Dict[str, Any]:
        """
        Optimize targeting parameters for massive datasets
        
        Args:
            data_size: Size of dataset in characters
            
        Returns:
            Optimization parameters
        """
        if data_size > 1e12:  # Trillion+ characters
            return {
                'chunk_size': 1e6,  # Process in 1MB chunks
                'max_hits_per_chunk': 100,
                'priority_threshold': 7,  # Only high-priority targets
                'parallel_processing': True,
                'memory_efficient': True,
                'target_types': ['start_codon', 'TATA_box', 'stop_codon']  # Essential targets only
            }
        elif data_size > 1e9:  # Billion+ characters
            return {
                'chunk_size': 1e5,  # Process in 100KB chunks
                'max_hits_per_chunk': 500,
                'priority_threshold': 5,
                'parallel_processing': True,
                'memory_efficient': True,
                'target_types': None  # All targets
            }
        else:
            return {
                'chunk_size': data_size,  # Process all at once
                'max_hits_per_chunk': 1000,
                'priority_threshold': 0,
                'parallel_processing': False,
                'memory_efficient': False,
                'target_types': None  # All targets
            }
    
    def process_massive_dataset(self, data: str, optimization_params: Dict[str, Any]) -> List[TargetHit]:
        """
        Process massive datasets with chunking and optimization
        
        Args:
            data: Genomic sequence data
            optimization_params: Optimization parameters
            
        Returns:
            List of target hits from entire dataset
        """
        chunk_size = int(optimization_params['chunk_size'])
        max_hits_per_chunk = optimization_params['max_hits_per_chunk']
        priority_threshold = optimization_params['priority_threshold']
        target_types = optimization_params['target_types']
        
        all_hits = []
        overlap_size = 1000  # Overlap between chunks to catch boundary targets
        
        for i in range(0, len(data), chunk_size - overlap_size):
            chunk_end = min(i + chunk_size, len(data))
            chunk = data[i:chunk_end]
            
            # Scan chunk for targets
            chunk_hits = self.scan_for_targets(
                chunk, 
                target_types=target_types,
                max_hits=max_hits_per_chunk
            )
            
            # Filter by priority threshold
            filtered_hits = [hit for hit in chunk_hits if hit.region.priority >= priority_threshold]
            
            # Adjust positions to global coordinates
            for hit in filtered_hits:
                hit.position += i
            
            all_hits.extend(filtered_hits)
            
            # Progress indicator for massive datasets
            if i % (chunk_size * 100) == 0:
                progress = (i / len(data)) * 100
                print(f"Processing: {progress:.1f}% complete")
        
        # Remove duplicates and sort
        unique_hits = self._remove_duplicate_hits(all_hits)
        unique_hits.sort(key=lambda x: (-x.region.priority, x.position))
        
        return unique_hits
    
    def _remove_duplicate_hits(self, hits: List[TargetHit]) -> List[TargetHit]:
        """Remove duplicate hits that are too close together"""
        if not hits:
            return hits
        
        unique_hits = []
        min_distance = 10  # Minimum distance between hits
        
        for hit in hits:
            is_duplicate = False
            for existing_hit in unique_hits:
                if (hit.region.name == existing_hit.region.name and 
                    abs(hit.position - existing_hit.position) < min_distance):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_hits.append(hit)
        
        return unique_hits
    
    def export_targets_config(self, filename: str = "targets_config.json"):
        """Export target configuration to JSON file"""
        config_data = {}
        
        for name, target in self.target_regions.items():
            config_data[name] = {
                'pattern': target.pattern,
                'region_type': target.region_type,
                'priority': target.priority,
                'context_left': target.context_left,
                'context_right': target.context_right,
                'description': target.description
            }
        
        with open(filename, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        print(f"Target configuration exported to: {filename}")
    
    def import_targets_config(self, filename: str):
        """Import target configuration from JSON file"""
        try:
            with open(filename, 'r') as f:
                config_data = json.load(f)
            
            for name, config in config_data.items():
                self.add_custom_target(
                    name=name,
                    pattern=config['pattern'],
                    region_type=config['region_type'],
                    priority=config['priority'],
                    context_left=config['context_left'],
                    context_right=config['context_right'],
                    description=config.get('description', '')
                )
            
            print(f"Target configuration imported from: {filename}")
            
        except Exception as e:
            print(f"Error importing target configuration: {e}")
    
    def get_target_statistics(self, hits: List[TargetHit]) -> Dict[str, Any]:
        """Generate statistics about target hits"""
        if not hits:
            return {}
        
        stats = {
            'total_hits': len(hits),
            'by_region_type': defaultdict(int),
            'by_target_name': defaultdict(int),
            'average_confidence': sum(hit.confidence for hit in hits) / len(hits),
            'high_confidence_hits': len([hit for hit in hits if hit.confidence > 0.8]),
            'priority_distribution': defaultdict(int)
        }
        
        for hit in hits:
            stats['by_region_type'][hit.region.region_type] += 1
            stats['by_target_name'][hit.region.name] += 1
            stats['priority_distribution'][hit.region.priority] += 1
        
        return dict(stats)

