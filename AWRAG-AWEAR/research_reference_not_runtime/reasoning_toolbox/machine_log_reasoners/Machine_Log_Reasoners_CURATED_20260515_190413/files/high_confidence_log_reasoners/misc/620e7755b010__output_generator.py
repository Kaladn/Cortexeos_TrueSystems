"""
Output Generator Module
Handles structured output formatting and result presentation
"""

import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
import statistics

class OutputGenerator:
    """Generates structured output from cascade processing results"""
    
    def __init__(self):
        self.output_formats = ['json', 'yaml', 'xml', 'csv', 'markdown', 'html']
        self.default_format = 'json'
        
    def generate_output(self, results: Dict[str, Any], config: Dict[str, Any], format_type: str = None) -> str:
        """
        Generate structured output from processing results
        
        Args:
            results: Processing results from cascade engine
            config: Configuration used for processing
            format_type: Output format ('json', 'yaml', 'xml', 'csv', 'markdown', 'html')
            
        Returns:
            Formatted output string
        """
        if format_type is None:
            format_type = self.default_format
            
        if format_type not in self.output_formats:
            format_type = self.default_format
            
        # Prepare comprehensive output data
        output_data = self._prepare_output_data(results, config)
        
        # Generate output based on format
        if format_type == 'json':
            return self._generate_json_output(output_data)
        elif format_type == 'yaml':
            return self._generate_yaml_output(output_data)
        elif format_type == 'xml':
            return self._generate_xml_output(output_data)
        elif format_type == 'csv':
            return self._generate_csv_output(output_data)
        elif format_type == 'markdown':
            return self._generate_markdown_output(output_data)
        elif format_type == 'html':
            return self._generate_html_output(output_data)
        else:
            return self._generate_json_output(output_data)
    
    def generate_scan_report(self, scan_results: Dict[str, Any]) -> str:
        """Generate a comprehensive scan report"""
        return self._generate_markdown_scan_report(scan_results)
    
    def generate_summary_report(self, results: Dict[str, Any], config: Dict[str, Any]) -> str:
        """Generate a summary report of processing results"""
        summary_data = self._create_summary_data(results, config)
        return self._generate_markdown_summary(summary_data)
    
    def _prepare_output_data(self, results: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare comprehensive output data structure"""
        output_data = {
            'metadata': {
                'generation_timestamp': datetime.now().isoformat(),
                'engine_version': '1.0.0',
                'processing_uuid': str(uuid.uuid4()),
                'configuration': config
            },
            'processing_summary': self._create_processing_summary(results, config),
            'cascade_results': results.get('cascade_results', {}),
            'bloom_results': results.get('bloom_results', {}),
            'anchor_results': results.get('anchor_results', {}),
            'target_results': results.get('target_results', {}),
            'prescan_results': results.get('prescan_results', {}),
            'analytics': self._generate_analytics(results),
            'performance_metrics': results.get('performance_metrics', {}),
            'quality_scores': self._calculate_quality_scores(results),
            'recommendations': self._generate_recommendations(results, config)
        }
        
        return output_data
    
    def _create_processing_summary(self, results: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Create processing summary"""
        summary = {
            'data_processed': {
                'total_length': results.get('data_length', 0),
                'segments_processed': results.get('segments_processed', 0),
                'cascade_levels': results.get('cascade_levels', 0)
            },
            'configuration_used': {
                'left_width': config.get('left_width', 0),
                'anchor_width': config.get('anchor_width', 0),
                'right_width': config.get('right_width', 0),
                'cascade_depth': config.get('cascade_depth', 0),
                'processing_mode': config.get('processing_mode', 'unknown')
            },
            'results_overview': {
                'bloom_nodes_processed': len(results.get('bloom_results', {})),
                'anchor_nodes_processed': len(results.get('anchor_results', {})),
                'targets_identified': len(results.get('target_results', {})),
                'confidence_scores': self._extract_confidence_scores(results)
            }
        }
        
        return summary
    
    def _generate_analytics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate analytics from results"""
        analytics = {
            'bloom_analytics': self._analyze_bloom_results(results.get('bloom_results', {})),
            'anchor_analytics': self._analyze_anchor_results(results.get('anchor_results', {})),
            'cascade_analytics': self._analyze_cascade_results(results.get('cascade_results', {})),
            'pattern_analytics': self._analyze_patterns(results),
            'efficiency_metrics': self._calculate_efficiency_metrics(results)
        }
        
        return analytics
    
    def _calculate_quality_scores(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate quality scores for results"""
        quality_scores = {
            'overall_quality': 0.0,
            'data_integrity': 0.0,
            'processing_accuracy': 0.0,
            'result_completeness': 0.0,
            'confidence_reliability': 0.0
        }
        
        # Calculate individual quality metrics
        bloom_results = results.get('bloom_results', {})
        anchor_results = results.get('anchor_results', {})
        
        if bloom_results:
            bloom_confidences = [result.get('confidence', 0) for result in bloom_results.values()]
            quality_scores['processing_accuracy'] = statistics.mean(bloom_confidences) if bloom_confidences else 0
        
        if anchor_results:
            anchor_confidences = [result.get('confidence', 0) for result in anchor_results.values()]
            quality_scores['confidence_reliability'] = statistics.mean(anchor_confidences) if anchor_confidences else 0
        
        # Data integrity based on successful processing
        total_expected = results.get('segments_processed', 1)
        total_processed = len(bloom_results) + len(anchor_results)
        quality_scores['data_integrity'] = min(1.0, total_processed / total_expected) if total_expected > 0 else 0
        
        # Result completeness
        expected_fields = ['bloom_results', 'anchor_results', 'cascade_results']
        present_fields = sum(1 for field in expected_fields if field in results and results[field])
        quality_scores['result_completeness'] = present_fields / len(expected_fields)
        
        # Overall quality
        quality_scores['overall_quality'] = statistics.mean([
            quality_scores['data_integrity'],
            quality_scores['processing_accuracy'],
            quality_scores['result_completeness'],
            quality_scores['confidence_reliability']
        ])
        
        return quality_scores
    
    def _generate_recommendations(self, results: Dict[str, Any], config: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on results"""
        recommendations = []
        
        # Analyze quality scores
        quality_scores = self._calculate_quality_scores(results)
        
        if quality_scores['overall_quality'] < 0.7:
            recommendations.append("Consider adjusting N-1-N configuration for better results")
        
        if quality_scores['processing_accuracy'] < 0.6:
            recommendations.append("Low processing accuracy detected - review target selection")
        
        if quality_scores['confidence_reliability'] < 0.5:
            recommendations.append("Low confidence scores - consider using different anchor/bloom functions")
        
        # Analyze cascade depth
        cascade_levels = results.get('cascade_levels', 0)
        if cascade_levels < 2:
            recommendations.append("Consider increasing cascade depth for more detailed analysis")
        elif cascade_levels > 5:
            recommendations.append("High cascade depth may be causing diminishing returns")
        
        # Analyze data characteristics
        data_length = results.get('data_length', 0)
        if data_length > 1000000:
            recommendations.append("Large dataset detected - consider using targeted analysis mode")
        
        return recommendations
    
    def _generate_json_output(self, output_data: Dict[str, Any]) -> str:
        """Generate JSON formatted output"""
        return json.dumps(output_data, indent=2, default=str)
    
    def _generate_yaml_output(self, output_data: Dict[str, Any]) -> str:
        """Generate YAML formatted output"""
        try:
            import yaml
            return yaml.dump(output_data, default_flow_style=False, indent=2)
        except ImportError:
            # Fallback to simple YAML-like format
            return self._simple_yaml_format(output_data)
    
    def _generate_xml_output(self, output_data: Dict[str, Any]) -> str:
        """Generate XML formatted output"""
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append('<sovereign_data_engine_results>')
        xml_lines.extend(self._dict_to_xml(output_data, indent=1))
        xml_lines.append('</sovereign_data_engine_results>')
        return '\n'.join(xml_lines)
    
    def _generate_csv_output(self, output_data: Dict[str, Any]) -> str:
        """Generate CSV formatted output (flattened structure)"""
        csv_lines = []
        
        # Flatten the data structure for CSV
        flattened_data = self._flatten_dict(output_data)
        
        # Create header
        headers = list(flattened_data.keys())
        csv_lines.append(','.join(headers))
        
        # Create data row
        values = [str(flattened_data[header]) for header in headers]
        csv_lines.append(','.join(values))
        
        return '\n'.join(csv_lines)
    
    def _generate_markdown_output(self, output_data: Dict[str, Any]) -> str:
        """Generate Markdown formatted output"""
        md_lines = []
        
        # Title
        md_lines.append('# Sovereign Data Cognition Engine Results')
        md_lines.append('')
        
        # Metadata
        metadata = output_data.get('metadata', {})
        md_lines.append('## Processing Metadata')
        md_lines.append(f"- **Generation Time**: {metadata.get('generation_timestamp', 'Unknown')}")
        md_lines.append(f"- **Engine Version**: {metadata.get('engine_version', 'Unknown')}")
        md_lines.append(f"- **Processing UUID**: {metadata.get('processing_uuid', 'Unknown')}")
        md_lines.append('')
        
        # Processing Summary
        summary = output_data.get('processing_summary', {})
        md_lines.append('## Processing Summary')
        
        data_processed = summary.get('data_processed', {})
        md_lines.append('### Data Processed')
        md_lines.append(f"- **Total Length**: {data_processed.get('total_length', 0):,} characters")
        md_lines.append(f"- **Segments Processed**: {data_processed.get('segments_processed', 0)}")
        md_lines.append(f"- **Cascade Levels**: {data_processed.get('cascade_levels', 0)}")
        md_lines.append('')
        
        config_used = summary.get('configuration_used', {})
        md_lines.append('### Configuration Used')
        md_lines.append(f"- **N-1-N Configuration**: {config_used.get('left_width', 0)}-{config_used.get('anchor_width', 0)}-{config_used.get('right_width', 0)}")
        md_lines.append(f"- **Cascade Depth**: {config_used.get('cascade_depth', 0)}")
        md_lines.append(f"- **Processing Mode**: {config_used.get('processing_mode', 'Unknown')}")
        md_lines.append('')
        
        # Quality Scores
        quality_scores = output_data.get('quality_scores', {})
        md_lines.append('## Quality Assessment')
        md_lines.append(f"- **Overall Quality**: {quality_scores.get('overall_quality', 0):.1%}")
        md_lines.append(f"- **Data Integrity**: {quality_scores.get('data_integrity', 0):.1%}")
        md_lines.append(f"- **Processing Accuracy**: {quality_scores.get('processing_accuracy', 0):.1%}")
        md_lines.append(f"- **Result Completeness**: {quality_scores.get('result_completeness', 0):.1%}")
        md_lines.append('')
        
        # Recommendations
        recommendations = output_data.get('recommendations', [])
        if recommendations:
            md_lines.append('## Recommendations')
            for rec in recommendations:
                md_lines.append(f"- {rec}")
            md_lines.append('')
        
        # Analytics Summary
        analytics = output_data.get('analytics', {})
        if analytics:
            md_lines.append('## Analytics Summary')
            
            bloom_analytics = analytics.get('bloom_analytics', {})
            if bloom_analytics:
                md_lines.append('### Bloom Analysis')
                md_lines.append(f"- **Total Bloom Nodes**: {bloom_analytics.get('total_nodes', 0)}")
                md_lines.append(f"- **Average Confidence**: {bloom_analytics.get('avg_confidence', 0):.1%}")
                md_lines.append('')
            
            anchor_analytics = analytics.get('anchor_analytics', {})
            if anchor_analytics:
                md_lines.append('### Anchor Analysis')
                md_lines.append(f"- **Total Anchor Nodes**: {anchor_analytics.get('total_nodes', 0)}")
                md_lines.append(f"- **Average Strength**: {anchor_analytics.get('avg_strength', 0):.1%}")
                md_lines.append('')
        
        return '\n'.join(md_lines)
    
    def _generate_html_output(self, output_data: Dict[str, Any]) -> str:
        """Generate HTML formatted output"""
        html_lines = []
        
        # HTML header
        html_lines.extend([
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head>',
            '    <meta charset="UTF-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            '    <title>Sovereign Data Cognition Engine Results</title>',
            '    <style>',
            '        body { font-family: Arial, sans-serif; margin: 20px; }',
            '        .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }',
            '        .section { margin: 20px 0; }',
            '        .metric { background-color: #e8f4f8; padding: 10px; margin: 5px 0; border-radius: 3px; }',
            '        .quality-high { color: green; font-weight: bold; }',
            '        .quality-medium { color: orange; font-weight: bold; }',
            '        .quality-low { color: red; font-weight: bold; }',
            '    </style>',
            '</head>',
            '<body>'
        ])
        
        # Content
        html_lines.append('    <div class="header">')
        html_lines.append('        <h1>Sovereign Data Cognition Engine Results</h1>')
        
        metadata = output_data.get('metadata', {})
        html_lines.append(f'        <p><strong>Generated:</strong> {metadata.get("generation_timestamp", "Unknown")}</p>')
        html_lines.append(f'        <p><strong>Processing UUID:</strong> {metadata.get("processing_uuid", "Unknown")}</p>')
        html_lines.append('    </div>')
        
        # Quality scores with color coding
        quality_scores = output_data.get('quality_scores', {})
        overall_quality = quality_scores.get('overall_quality', 0)
        quality_class = 'quality-high' if overall_quality > 0.8 else 'quality-medium' if overall_quality > 0.6 else 'quality-low'
        
        html_lines.append('    <div class="section">')
        html_lines.append('        <h2>Quality Assessment</h2>')
        html_lines.append(f'        <div class="metric">Overall Quality: <span class="{quality_class}">{overall_quality:.1%}</span></div>')
        html_lines.append(f'        <div class="metric">Data Integrity: {quality_scores.get("data_integrity", 0):.1%}</div>')
        html_lines.append(f'        <div class="metric">Processing Accuracy: {quality_scores.get("processing_accuracy", 0):.1%}</div>')
        html_lines.append('    </div>')
        
        # Processing summary
        summary = output_data.get('processing_summary', {})
        data_processed = summary.get('data_processed', {})
        
        html_lines.append('    <div class="section">')
        html_lines.append('        <h2>Processing Summary</h2>')
        html_lines.append(f'        <div class="metric">Data Length: {data_processed.get("total_length", 0):,} characters</div>')
        html_lines.append(f'        <div class="metric">Segments Processed: {data_processed.get("segments_processed", 0)}</div>')
        html_lines.append(f'        <div class="metric">Cascade Levels: {data_processed.get("cascade_levels", 0)}</div>')
        html_lines.append('    </div>')
        
        # HTML footer
        html_lines.extend([
            '</body>',
            '</html>'
        ])
        
        return '\n'.join(html_lines)
    
    def _generate_markdown_scan_report(self, scan_results: Dict[str, Any]) -> str:
        """Generate markdown scan report"""
        md_lines = []
        
        md_lines.append('# Pre-Scan Analysis Report')
        md_lines.append('')
        
        # Data profile
        profile = scan_results.get('data_profile', {})
        md_lines.append('## Data Profile')
        md_lines.append(f"- **Total Length**: {profile.get('total_length', 0):,} characters")
        md_lines.append(f"- **Unique Characters**: {profile.get('unique_characters', 0)}")
        md_lines.append(f"- **Character Diversity**: {profile.get('character_diversity', 0):.1%}")
        md_lines.append('')
        
        # Data type indicators
        type_indicators = profile.get('data_type_indicators', {})
        if type_indicators:
            md_lines.append('### Data Type Analysis')
            for data_type, confidence in type_indicators.items():
                md_lines.append(f"- **{data_type.title()}**: {confidence:.1%}")
            md_lines.append('')
        
        # Structural analysis
        structure = scan_results.get('structural_analysis', {})
        if structure:
            md_lines.append('## Structural Analysis')
            
            line_structure = structure.get('line_structure', {})
            if line_structure:
                md_lines.append('### Line Structure')
                md_lines.append(f"- **Line Count**: {line_structure.get('line_count', 0)}")
                md_lines.append(f"- **Average Line Length**: {line_structure.get('avg_line_length', 0):.1f}")
                md_lines.append('')
            
            periodicity = structure.get('periodicity', {})
            if periodicity.get('is_periodic', False):
                strongest = periodicity.get('strongest_period', {})
                md_lines.append('### Periodicity Detected')
                md_lines.append(f"- **Period**: {strongest.get('period', 0)}")
                md_lines.append(f"- **Strength**: {strongest.get('strength', 0):.1%}")
                md_lines.append('')
        
        # Complexity analysis
        complexity = scan_results.get('complexity_analysis', {})
        if complexity:
            md_lines.append('## Complexity Analysis')
            md_lines.append(f"- **Global Complexity**: {complexity.get('global_complexity', 0):.1%}")
            md_lines.append(f"- **Information Content**: {complexity.get('information_content', 0):.2f}")
            md_lines.append('')
        
        return '\n'.join(md_lines)
    
    # Helper methods
    def _analyze_bloom_results(self, bloom_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze bloom results for analytics"""
        if not bloom_results:
            return {'total_nodes': 0, 'avg_confidence': 0}
        
        confidences = [result.get('confidence', 0) for result in bloom_results.values()]
        
        return {
            'total_nodes': len(bloom_results),
            'avg_confidence': statistics.mean(confidences) if confidences else 0,
            'confidence_variance': statistics.variance(confidences) if len(confidences) > 1 else 0,
            'max_confidence': max(confidences) if confidences else 0,
            'min_confidence': min(confidences) if confidences else 0
        }
    
    def _analyze_anchor_results(self, anchor_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze anchor results for analytics"""
        if not anchor_results:
            return {'total_nodes': 0, 'avg_strength': 0}
        
        strengths = []
        confidences = []
        
        for result in anchor_results.values():
            metadata = result.get('metadata', {})
            strengths.append(metadata.get('anchor_strength', 0))
            confidences.append(result.get('confidence', 0))
        
        return {
            'total_nodes': len(anchor_results),
            'avg_strength': statistics.mean(strengths) if strengths else 0,
            'avg_confidence': statistics.mean(confidences) if confidences else 0,
            'strength_variance': statistics.variance(strengths) if len(strengths) > 1 else 0
        }
    
    def _analyze_cascade_results(self, cascade_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze cascade results for analytics"""
        return {
            'total_levels': cascade_results.get('levels_processed', 0),
            'total_nodes': cascade_results.get('total_nodes_processed', 0),
            'processing_efficiency': cascade_results.get('efficiency_score', 0)
        }
    
    def _analyze_patterns(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze patterns across all results"""
        return {
            'pattern_diversity': 0.5,  # Placeholder
            'pattern_consistency': 0.7,  # Placeholder
            'recurring_patterns': []  # Placeholder
        }
    
    def _calculate_efficiency_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate processing efficiency metrics"""
        performance = results.get('performance_metrics', {})
        
        return {
            'processing_time': performance.get('total_time', 0),
            'throughput': performance.get('characters_per_second', 0),
            'memory_efficiency': performance.get('memory_usage_ratio', 0),
            'cpu_utilization': performance.get('cpu_utilization', 0)
        }
    
    def _extract_confidence_scores(self, results: Dict[str, Any]) -> Dict[str, float]:
        """Extract confidence scores from results"""
        bloom_results = results.get('bloom_results', {})
        anchor_results = results.get('anchor_results', {})
        
        bloom_confidences = [result.get('confidence', 0) for result in bloom_results.values()]
        anchor_confidences = [result.get('confidence', 0) for result in anchor_results.values()]
        
        all_confidences = bloom_confidences + anchor_confidences
        
        return {
            'average': statistics.mean(all_confidences) if all_confidences else 0,
            'minimum': min(all_confidences) if all_confidences else 0,
            'maximum': max(all_confidences) if all_confidences else 0,
            'variance': statistics.variance(all_confidences) if len(all_confidences) > 1 else 0
        }
    
    def _create_summary_data(self, results: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Create summary data for reports"""
        return {
            'processing_overview': self._create_processing_summary(results, config),
            'key_findings': self._extract_key_findings(results),
            'performance_summary': self._summarize_performance(results),
            'quality_assessment': self._calculate_quality_scores(results)
        }
    
    def _extract_key_findings(self, results: Dict[str, Any]) -> List[str]:
        """Extract key findings from results"""
        findings = []
        
        bloom_results = results.get('bloom_results', {})
        anchor_results = results.get('anchor_results', {})
        
        if bloom_results:
            findings.append(f"Processed {len(bloom_results)} bloom nodes")
        
        if anchor_results:
            findings.append(f"Identified {len(anchor_results)} anchor points")
        
        # Add more sophisticated finding extraction here
        
        return findings
    
    def _summarize_performance(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize performance metrics"""
        performance = results.get('performance_metrics', {})
        
        return {
            'total_processing_time': performance.get('total_time', 0),
            'average_node_time': performance.get('avg_node_time', 0),
            'memory_peak': performance.get('peak_memory', 0),
            'efficiency_rating': performance.get('efficiency_score', 0)
        }
    
    def _generate_markdown_summary(self, summary_data: Dict[str, Any]) -> str:
        """Generate markdown summary report"""
        md_lines = []
        
        md_lines.append('# Processing Summary Report')
        md_lines.append('')
        
        # Key findings
        findings = summary_data.get('key_findings', [])
        if findings:
            md_lines.append('## Key Findings')
            for finding in findings:
                md_lines.append(f"- {finding}")
            md_lines.append('')
        
        # Quality assessment
        quality = summary_data.get('quality_assessment', {})
        md_lines.append('## Quality Assessment')
        md_lines.append(f"- **Overall Quality**: {quality.get('overall_quality', 0):.1%}")
        md_lines.append(f"- **Data Integrity**: {quality.get('data_integrity', 0):.1%}")
        md_lines.append('')
        
        # Performance summary
        performance = summary_data.get('performance_summary', {})
        md_lines.append('## Performance Summary')
        md_lines.append(f"- **Total Processing Time**: {performance.get('total_processing_time', 0):.2f} seconds")
        md_lines.append(f"- **Efficiency Rating**: {performance.get('efficiency_rating', 0):.1%}")
        md_lines.append('')
        
        return '\n'.join(md_lines)
    
    # Utility methods for format conversion
    def _simple_yaml_format(self, data: Dict[str, Any], indent: int = 0) -> str:
        """Simple YAML-like formatting"""
        lines = []
        prefix = '  ' * indent
        
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(self._simple_yaml_format(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                for item in value:
                    lines.append(f"{prefix}  - {item}")
            else:
                lines.append(f"{prefix}{key}: {value}")
        
        return '\n'.join(lines)
    
    def _dict_to_xml(self, data: Dict[str, Any], indent: int = 0) -> List[str]:
        """Convert dictionary to XML format"""
        lines = []
        prefix = '  ' * indent
        
        for key, value in data.items():
            safe_key = key.replace(' ', '_').replace('-', '_')
            
            if isinstance(value, dict):
                lines.append(f"{prefix}<{safe_key}>")
                lines.extend(self._dict_to_xml(value, indent + 1))
                lines.append(f"{prefix}</{safe_key}>")
            elif isinstance(value, list):
                lines.append(f"{prefix}<{safe_key}>")
                for item in value:
                    lines.append(f"{prefix}  <item>{item}</item>")
                lines.append(f"{prefix}</{safe_key}>")
            else:
                lines.append(f"{prefix}<{safe_key}>{value}</{safe_key}>")
        
        return lines
    
    def _flatten_dict(self, data: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary for CSV output"""
        items = []
        
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            
            if isinstance(value, dict):
                items.extend(self._flatten_dict(value, new_key, sep=sep).items())
            elif isinstance(value, list):
                items.append((new_key, '; '.join(map(str, value))))
            else:
                items.append((new_key, value))
        
        return dict(items)

