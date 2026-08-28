"""
Simple Output Generator - NO ERRORS VERSION
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

class OutputGenerator:
    """Simple output generator that handles list results properly"""
    
    def __init__(self):
        self.output_formats = ['json', 'yaml', 'csv', 'markdown']
        self.default_format = 'json'
        
    def generate_output(self, results: List[Dict[str, Any]], config: Dict[str, Any], format_type: str = None) -> str:
        """
        Generate output from list of results (not dict)
        
        Args:
            results: List of processing results from cascade engine
            config: Configuration used for processing
            format_type: Output format
            
        Returns:
            Formatted output string
        """
        if format_type is None:
            format_type = self.default_format
            
        # Prepare simple output data
        output_data = {
            'metadata': {
                'generation_timestamp': datetime.now().isoformat(),
                'total_results': len(results),
                'configuration': config
            },
            'summary': {
                'segments_processed': len(results),
                'anchor_segments': len([r for r in results if r.get('node_type') == 'anchor']),
                'bloom_segments': len([r for r in results if r.get('node_type') == 'bloom']),
                'average_confidence': sum(r.get('confidence', 0) for r in results) / len(results) if results else 0
            },
            'results': results[:100]  # Limit to first 100 for readability
        }
        
        if format_type == 'json':
            return json.dumps(output_data, indent=2)
        elif format_type == 'markdown':
            return self._generate_markdown_output(output_data)
        else:
            return json.dumps(output_data, indent=2)
    
    def _generate_markdown_output(self, data: Dict[str, Any]) -> str:
        """Generate markdown output"""
        md = f"""# Cascade Processing Results

## Summary
- **Total Segments Processed:** {data['summary']['segments_processed']:,}
- **Anchor Segments:** {data['summary']['anchor_segments']:,}
- **Bloom Segments:** {data['summary']['bloom_segments']:,}
- **Average Confidence:** {data['summary']['average_confidence']:.3f}
- **Generated:** {data['metadata']['generation_timestamp']}

## Configuration
```json
{json.dumps(data['metadata']['configuration'], indent=2)}
```

## Sample Results
"""
        
        # Add sample results
        for i, result in enumerate(data['results'][:10]):
            md += f"""
### Result {i+1}
- **Type:** {result.get('node_type', 'unknown')}
- **Position:** {result.get('position', 0):,}
- **Confidence:** {result.get('confidence', 0):.3f}
- **Data:** `{result.get('data', '')[:50]}...`
"""
        
        return md
    
    def save_results(self, results: List[Dict[str, Any]], config: Dict[str, Any], 
                    output_path: str, format_type: str = 'json') -> bool:
        """Save results to file"""
        try:
            output_content = self.generate_output(results, config, format_type)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)
            
            print(f"✅ Results saved to: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")
            return False

