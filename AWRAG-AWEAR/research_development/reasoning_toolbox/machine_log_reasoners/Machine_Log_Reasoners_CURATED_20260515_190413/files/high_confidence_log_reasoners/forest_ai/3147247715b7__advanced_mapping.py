"""
🌲 Forest AI - Advanced Mapping Plugin
Extends core mapping with specialized analysis features
"""

from typing import Dict, Any, List
from pathlib import Path
import json
from datetime import datetime

# Import the plugin base class
import sys
sys.path.append(str(Path(__file__).parent.parent))
from bridges.forest_plugins import PluginBase, PluginManifest


class AdvancedMappingPlugin(PluginBase):
    """
    Advanced document mapping plugin with additional analysis features:
    - Batch mapping with progress tracking
    - Coverage comparison across documents
    - Token frequency analysis
    - Vocabulary recommendations
    - Export reports in multiple formats
    """
    
    def __init__(self):
        self.name = "advanced_mapping"
        self.version = "1.0.0"
        self.bridge_url = "http://127.0.0.1:5050"
        self.storage_dir = Path("data/plugins/advanced_mapping")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            name=self.name,
            version=self.version,
            author="Forest AI Team",
            description="Advanced document mapping with batch processing, coverage comparison, and vocabulary recommendations",
            capabilities=[
                "batch_mapping",
                "coverage_analysis",
                "vocabulary_recommendations",
                "export_formats"
            ],
            endpoints={
                "map_batch": "map_batch_documents",
                "compare": "compare_coverage",
                "recommend": "recommend_vocabulary",
                "export": "export_report",
                "history": "get_mapping_history"
            },
            config_schema={
                "auto_save": True,
                "min_coverage_threshold": 70.0,
                "export_formats": ["json", "csv", "markdown", "html"]
            }
        )
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize plugin with configuration"""
        self.config = {
            "auto_save": config.get("auto_save", True),
            "min_coverage_threshold": config.get("min_coverage_threshold", 70.0),
            "export_formats": config.get("export_formats", ["json", "csv", "markdown"])
        }
        
        # Create history file if it doesn't exist
        self.history_file = self.storage_dir / "mapping_history.json"
        if not self.history_file.exists():
            with open(self.history_file, 'w') as f:
                json.dump({"mappings": []}, f)
        
        print(f"✅ {self.name} plugin initialized")
        return True
    
    def map_batch_documents(self, documents: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Map multiple documents in batch
        
        Args:
            documents: List of {"filename": str, "content": str}
        
        Returns:
            Batch mapping results with summary statistics
        """
        import requests
        
        results = []
        total_tokens = 0
        total_mapped = 0
        total_unmapped = 0
        
        for idx, doc in enumerate(documents, 1):
            try:
                response = requests.post(
                    f"{self.bridge_url}/api/map",
                    json={
                        "text": doc["content"],
                        "filename": doc["filename"]
                    },
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    results.append({
                        "filename": doc["filename"],
                        "status": "success",
                        "total_tokens": result.get("total_tokens", 0),
                        "mapped_tokens": result.get("mapped_tokens", 0),
                        "coverage_pct": result.get("coverage_pct", 0)
                    })
                    
                    total_tokens += result.get("total_tokens", 0)
                    total_mapped += result.get("mapped_tokens", 0)
                    total_unmapped += result.get("unmapped_tokens", 0)
                    
                    # Save to history
                    self._save_to_history(doc["filename"], result)
                else:
                    results.append({
                        "filename": doc["filename"],
                        "status": "error",
                        "error": f"HTTP {response.status_code}"
                    })
            
            except Exception as e:
                results.append({
                    "filename": doc["filename"],
                    "status": "error",
                    "error": str(e)
                })
        
        avg_coverage = (total_mapped / total_tokens * 100) if total_tokens > 0 else 0
        
        return {
            "batch_id": datetime.utcnow().strftime("%Y%m%d-%H%M%S"),
            "total_documents": len(documents),
            "successful": sum(1 for r in results if r["status"] == "success"),
            "failed": sum(1 for r in results if r["status"] == "error"),
            "total_tokens": total_tokens,
            "total_mapped": total_mapped,
            "total_unmapped": total_unmapped,
            "average_coverage": round(avg_coverage, 2),
            "results": results
        }
    
    def compare_coverage(self, filenames: List[str]) -> Dict[str, Any]:
        """
        Compare coverage across multiple mapped documents
        
        Args:
            filenames: List of document names to compare
        
        Returns:
            Comparison analysis with rankings
        """
        history = self._load_history()
        
        # Find matching mappings
        mappings = []
        for entry in history["mappings"]:
            if entry["filename"] in filenames:
                mappings.append(entry)
        
        if not mappings:
            return {"error": "No mappings found for specified files"}
        
        # Sort by coverage
        sorted_mappings = sorted(mappings, key=lambda x: x["coverage_pct"], reverse=True)
        
        return {
            "comparison_count": len(mappings),
            "best_coverage": {
                "filename": sorted_mappings[0]["filename"],
                "coverage": sorted_mappings[0]["coverage_pct"]
            },
            "worst_coverage": {
                "filename": sorted_mappings[-1]["filename"],
                "coverage": sorted_mappings[-1]["coverage_pct"]
            },
            "average_coverage": round(sum(m["coverage_pct"] for m in mappings) / len(mappings), 2),
            "rankings": [
                {
                    "rank": idx + 1,
                    "filename": m["filename"],
                    "coverage": m["coverage_pct"],
                    "total_tokens": m["total_tokens"],
                    "unmapped_tokens": m["unmapped_tokens"]
                }
                for idx, m in enumerate(sorted_mappings)
            ]
        }
    
    def recommend_vocabulary(self, filename: str, top_n: int = 20) -> Dict[str, Any]:
        """
        Recommend vocabulary additions based on unmapped token frequency
        
        Args:
            filename: Document to analyze
            top_n: Number of recommendations to return
        
        Returns:
            Top unmapped tokens recommended for lexicon addition
        """
        history = self._load_history()
        
        # Find the mapping
        mapping = next((m for m in history["mappings"] if m["filename"] == filename), None)
        
        if not mapping:
            return {"error": f"No mapping found for {filename}"}
        
        unmapped = mapping.get("unmapped_detail", {})
        
        if not unmapped:
            return {
                "filename": filename,
                "recommendations": [],
                "message": "Document has perfect coverage - no recommendations needed!"
            }
        
        # Sort by occurrence frequency
        sorted_tokens = sorted(
            unmapped.items(),
            key=lambda x: x[1].get("total_occurrences", 0),
            reverse=True
        )[:top_n]
        
        recommendations = [
            {
                "token": token,
                "occurrences": data.get("total_occurrences", 0),
                "contexts": data.get("contexts", [])[:3],  # First 3 contexts
                "priority": "high" if data.get("total_occurrences", 0) > 10 else "medium" if data.get("total_occurrences", 0) > 5 else "low"
            }
            for token, data in sorted_tokens
        ]
        
        return {
            "filename": filename,
            "current_coverage": mapping["coverage_pct"],
            "potential_coverage_gain": round(
                (sum(r["occurrences"] for r in recommendations) / mapping["total_tokens"]) * 100, 2
            ),
            "recommendations": recommendations
        }
    
    def export_report(self, filename: str, format: str = "json") -> Dict[str, Any]:
        """
        Export mapping report in specified format
        
        Args:
            filename: Document to export
            format: Export format (json, csv, markdown, html)
        
        Returns:
            Export result with file path
        """
        history = self._load_history()
        mapping = next((m for m in history["mappings"] if m["filename"] == filename), None)
        
        if not mapping:
            return {"error": f"No mapping found for {filename}"}
        
        export_dir = self.storage_dir / "exports"
        export_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        
        if format == "json":
            output_file = export_dir / f"{filename}_{timestamp}.json"
            with open(output_file, 'w') as f:
                json.dump(mapping, f, indent=2)
        
        elif format == "csv":
            output_file = export_dir / f"{filename}_{timestamp}.csv"
            with open(output_file, 'w') as f:
                f.write("Token,Mapped,Occurrences,Symbol\n")
                for token, data in mapping.get("map_616", {}).items():
                    f.write(f'"{token}",Yes,{data.get("frequency", 0)},{data.get("symbol", "")}\n')
                for token, data in mapping.get("unmapped_detail", {}).items():
                    f.write(f'"{token}",No,{data.get("total_occurrences", 0)},\n')
        
        elif format == "markdown":
            output_file = export_dir / f"{filename}_{timestamp}.md"
            with open(output_file, 'w') as f:
                f.write(f"# Mapping Report: {filename}\n\n")
                f.write(f"**Coverage:** {mapping['coverage_pct']}%\n")
                f.write(f"**Total Tokens:** {mapping['total_tokens']}\n")
                f.write(f"**Mapped:** {mapping['mapped_tokens']}\n")
                f.write(f"**Unmapped:** {mapping['unmapped_tokens']}\n\n")
                f.write("## Top Unmapped Tokens\n\n")
                unmapped = mapping.get("unmapped_detail", {})
                for token, data in sorted(unmapped.items(), key=lambda x: x[1].get("total_occurrences", 0), reverse=True)[:20]:
                    f.write(f"- **{token}**: {data.get('total_occurrences', 0)} occurrences\n")
        
        elif format == "html":
            output_file = export_dir / f"{filename}_{timestamp}.html"
            with open(output_file, 'w') as f:
                f.write(f"""<!DOCTYPE html>
<html>
<head><title>Mapping Report: {filename}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 40px; }}
.stat {{ background: #f0f0f0; padding: 15px; margin: 10px 0; border-radius: 5px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background-color: #4CAF50; color: white; }}
</style>
</head>
<body>
<h1>Mapping Report: {filename}</h1>
<div class="stat"><strong>Coverage:</strong> {mapping['coverage_pct']}%</div>
<div class="stat"><strong>Total Tokens:</strong> {mapping['total_tokens']}</div>
<div class="stat"><strong>Mapped:</strong> {mapping['mapped_tokens']}</div>
<div class="stat"><strong>Unmapped:</strong> {mapping['unmapped_tokens']}</div>
<h2>Top Unmapped Tokens</h2>
<table>
<tr><th>Token</th><th>Occurrences</th></tr>
""")
                unmapped = mapping.get("unmapped_detail", {})
                for token, data in sorted(unmapped.items(), key=lambda x: x[1].get("total_occurrences", 0), reverse=True)[:20]:
                    f.write(f"<tr><td>{token}</td><td>{data.get('total_occurrences', 0)}</td></tr>\n")
                f.write("</table></body></html>")
        
        else:
            return {"error": f"Unsupported format: {format}"}
        
        return {
            "success": True,
            "format": format,
            "output_file": str(output_file),
            "size_bytes": output_file.stat().st_size
        }
    
    def get_mapping_history(self, limit: int = 50) -> Dict[str, Any]:
        """Get recent mapping history"""
        history = self._load_history()
        
        recent = sorted(
            history["mappings"],
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )[:limit]
        
        return {
            "total_mappings": len(history["mappings"]),
            "recent_count": len(recent),
            "recent_mappings": recent
        }
    
    def _save_to_history(self, filename: str, result: Dict[str, Any]):
        """Save mapping result to history"""
        if not self.config.get("auto_save", True):
            return
        
        history = self._load_history()
        
        entry = {
            "filename": filename,
            "timestamp": datetime.utcnow().isoformat(),
            "total_tokens": result.get("total_tokens", 0),
            "mapped_tokens": result.get("mapped_tokens", 0),
            "unmapped_tokens": result.get("unmapped_tokens", 0),
            "coverage_pct": result.get("coverage_pct", 0),
            "map_616": result.get("map_616", {}),
            "unmapped_detail": result.get("unmapped_detail", {})
        }
        
        history["mappings"].append(entry)
        
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def _load_history(self) -> Dict[str, Any]:
        """Load mapping history from file"""
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except:
            return {"mappings": []}
    
    def shutdown(self) -> bool:
        """Cleanup on plugin shutdown"""
        print(f"🛑 {self.name} plugin shutting down")
        return True


# Plugin instance for registration
plugin = AdvancedMappingPlugin()
