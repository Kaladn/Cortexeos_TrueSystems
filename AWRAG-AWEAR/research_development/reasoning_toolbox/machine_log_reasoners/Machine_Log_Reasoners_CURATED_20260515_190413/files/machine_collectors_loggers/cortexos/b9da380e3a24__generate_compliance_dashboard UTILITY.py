"""
CortexOS Temporal Cognition v2.1
Module: Compliance Dashboard Generator
Purpose: Generates HTML and JSON dashboards for Agharmonic Law compliance monitoring
"""

import os
import json
import datetime
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def generate_compliance_json_dashboard(neural_map_path, output_path):
    """
    Generate a JSON compliance dashboard from neural_map.json
    
    Args:
        neural_map_path: Path to neural_map.json
        output_path: Path to save the JSON dashboard
    """
    try:
        # Load neural map
        with open(neural_map_path, 'r') as f:
            neural_map = json.load(f)
        
        # Extract compliance data
        modules = neural_map['modules']
        compliance_data = {
            "meta": {
                "generated_at": datetime.datetime.utcnow().isoformat(),
                "total_modules": len(modules),
                "compliance_summary": neural_map.get('compliance_summary', {})
            },
            "modules": {}
        }
        
        # Process each module
        for module_id, module_data in modules.items():
            compliance_info = module_data.get('agharmonic_compliance', {})
            compliance_data['modules'][module_id] = {
                "path": module_data.get('path', ''),
                "type": module_data.get('type', ''),
                "status": compliance_info.get('status', 'unknown'),
                "compliance_level": compliance_info.get('compliance_level', 0.0),
                "last_verified": compliance_info.get('last_verified', None),
                "methods": compliance_info.get('methods', {}),
                "issues": compliance_info.get('issues', [])
            }
        
        # Write to output file
        with open(output_path, 'w') as f:
            json.dump(compliance_data, f, indent=2)
            
        print(f"JSON compliance dashboard generated at {output_path}")
        return True
    
    except Exception as e:
        print(f"Error generating JSON compliance dashboard: {e}")
        return False

def generate_compliance_html_dashboard(neural_map_path, output_path):
    """
    Generate an HTML compliance dashboard from neural_map.json
    
    Args:
        neural_map_path: Path to neural_map.json
        output_path: Path to save the HTML dashboard
    """
    try:
        # Load neural map
        with open(neural_map_path, 'r') as f:
            neural_map = json.load(f)
        
        # Extract compliance data
        modules = neural_map['modules']
        compliance_summary = neural_map.get('compliance_summary', {})
        
        # Start building HTML
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CortexOS Agharmonic Compliance Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 5px 5px 0 0;
        }
        h1 {
            margin: 0;
            font-size: 24px;
        }
        .summary {
            display: flex;
            justify-content: space-between;
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .summary-item {
            text-align: center;
            padding: 10px;
        }
        .summary-item h3 {
            margin: 0;
            font-size: 14px;
            color: #7f8c8d;
        }
        .summary-item p {
            margin: 5px 0 0;
            font-size: 24px;
            font-weight: bold;
        }
        .progress-container {
            margin-top: 5px;
            background-color: #ddd;
            border-radius: 10px;
            height: 10px;
            width: 100%;
        }
        .progress-bar {
            height: 10px;
            border-radius: 10px;
            background-color: #27ae60;
        }
        .module-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .module-card {
            background-color: white;
            border-radius: 5px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .module-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }
        .module-title {
            font-weight: bold;
            font-size: 16px;
        }
        .module-path {
            color: #7f8c8d;
            font-size: 12px;
            margin-top: 5px;
        }
        .module-type {
            background-color: #3498db;
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
        }
        .compliance-badge {
            padding: 5px 10px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
            color: white;
        }
        .compliant {
            background-color: #27ae60;
        }
        .partial {
            background-color: #f39c12;
        }
        .pending {
            background-color: #e74c3c;
        }
        .methods-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 5px;
            margin-top: 10px;
        }
        .method-item {
            font-size: 12px;
            padding: 5px;
            border-radius: 3px;
            text-align: center;
        }
        .method-compliant {
            background-color: rgba(39, 174, 96, 0.2);
            color: #27ae60;
        }
        .method-partial {
            background-color: rgba(243, 156, 18, 0.2);
            color: #f39c12;
        }
        .method-missing {
            background-color: rgba(231, 76, 60, 0.2);
            color: #e74c3c;
        }
        .issues-list {
            margin-top: 10px;
            font-size: 12px;
            color: #e74c3c;
        }
        .issues-list ul {
            margin: 5px 0 0;
            padding-left: 20px;
        }
        .last-verified {
            font-size: 11px;
            color: #95a5a6;
            margin-top: 10px;
            text-align: right;
        }
        .phase-section {
            margin-top: 30px;
        }
        .phase-header {
            background-color: #34495e;
            color: white;
            padding: 10px 15px;
            border-radius: 5px;
            margin-bottom: 15px;
        }
        .phase-header h2 {
            margin: 0;
            font-size: 18px;
        }
        footer {
            margin-top: 30px;
            text-align: center;
            color: #7f8c8d;
            font-size: 12px;
            padding: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>CortexOS Temporal Cognition v2.1 - Agharmonic Compliance Dashboard</h1>
        </header>
        
        <div class="summary">
            <div class="summary-item">
                <h3>Total Modules</h3>
                <p>{total_modules}</p>
            </div>
            <div class="summary-item">
                <h3>Fully Compliant</h3>
                <p>{fully_compliant}</p>
            </div>
            <div class="summary-item">
                <h3>Partially Compliant</h3>
                <p>{partially_compliant}</p>
            </div>
            <div class="summary-item">
                <h3>Pending Purification</h3>
                <p>{pending_purification}</p>
            </div>
            <div class="summary-item">
                <h3>Overall Compliance</h3>
                <p>{compliance_percentage}%</p>
                <div class="progress-container">
                    <div class="progress-bar" style="width: {compliance_percentage}%"></div>
                </div>
            </div>
        </div>
        """.format(
            total_modules=compliance_summary.get('total_modules', len(modules)),
            fully_compliant=compliance_summary.get('fully_compliant', 0),
            partially_compliant=compliance_summary.get('partially_compliant', 0),
            pending_purification=compliance_summary.get('pending_purification', 0),
            compliance_percentage=compliance_summary.get('compliance_percentage', 0)
        )
        
        # Global Sync Core Section
        html += """
        <div class="phase-section">
            <div class="phase-header">
                <h2>Global Sync Core</h2>
            </div>
            <div class="module-grid">
        """
        
        # Add Global Sync Core modules
        sync_core_modules = ['global_sync_manager', 'neural_fabric', 'resonance_monitor', 'context_engine', 'adaptive_learning']
        for module_id in sync_core_modules:
            if module_id in modules:
                html += generate_module_card_html(module_id, modules[module_id])
        
        html += """
            </div>
        </div>
        """
        
        # Phase 1 Section
        html += """
        <div class="phase-section">
            <div class="phase-header">
                <h2>Phase 1: Critical Core</h2>
            </div>
            <div class="module-grid">
        """
        
        # Add Phase 1 modules
        phase1_modules = ['neuroengine', 'resonance_field', 'phase_harmonics', 'cortex_vectorizer', 'neural_gatekeeper']
        for module_id in phase1_modules:
            if module_id in modules:
                html += generate_module_card_html(module_id, modules[module_id])
        
        html += """
            </div>
        </div>
        """
        
        # Phase 2 Section
        html += """
        <div class="phase-section">
            <div class="phase-header">
                <h2>Phase 2: Resonance Chain</h2>
            </div>
            <div class="module-grid">
        """
        
        # Add Phase 2 modules
        phase2_modules = ['swarm_resonance', 'resonance_reinforcer', 'topk_sparse_resonance', 'chord_resonator']
        for module_id in phase2_modules:
            if module_id in modules:
                html += generate_module_card_html(module_id, modules[module_id])
        
        html += """
            </div>
        </div>
        """
        
        # All Other Modules Section
        html += """
        <div class="phase-section">
            <div class="phase-header">
                <h2>All Other Modules</h2>
            </div>
            <div class="module-grid">
        """
        
        # Add all other modules
        excluded_modules = sync_core_modules + phase1_modules + phase2_modules
        for module_id, module_data in modules.items():
            if module_id not in excluded_modules:
                html += generate_module_card_html(module_id, module_data)
        
        html += """
            </div>
        </div>
        """
        
        # Footer
        html += """
        <footer>
            <p>Generated on {timestamp} • CortexOS Temporal Cognition v2.1</p>
        </footer>
    </div>
</body>
</html>
        """.format(timestamp=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"))
        
        # Write to output file
        with open(output_path, 'w') as f:
            f.write(html)
            
        print(f"HTML compliance dashboard generated at {output_path}")
        return True
    
    except Exception as e:
        print(f"Error generating HTML compliance dashboard: {e}")
        return False

def generate_module_card_html(module_id, module_data):
    """Generate HTML for a module card"""
    compliance_info = module_data.get('agharmonic_compliance', {})
    status = compliance_info.get('status', 'unknown')
    compliance_level = compliance_info.get('compliance_level', 0.0)
    last_verified = compliance_info.get('last_verified', '')
    methods = compliance_info.get('methods', {})
    issues = compliance_info.get('issues', [])
    
    # Determine status class
    status_class = 'pending'
    if status == 'compliant':
        status_class = 'compliant'
    elif status == 'partial':
        status_class = 'partial'
    
    # Format methods grid
    methods_html = '<div class="methods-grid">'
    for method_name, method_status in methods.items():
        method_class = 'method-missing'
        if method_status == 'compliant':
            method_class = 'method-compliant'
        elif method_status == 'partial':
            method_class = 'method-partial'
        
        methods_html += f'<div class="method-item {method_class}">{method_name}</div>'
    methods_html += '</div>'
    
    # Format issues list
    issues_html = ''
    if issues:
        issues_html = '<div class="issues-list"><strong>Issues:</strong><ul>'
        for issue in issues:
            issues_html += f'<li>{issue}</li>'
        issues_html += '</ul></div>'
    
    # Format last verified
    last_verified_html = ''
    if last_verified:
        try:
            # Try to parse and format the timestamp
            dt = datetime.datetime.fromisoformat(last_verified)
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            last_verified_html = f'<div class="last-verified">Last verified: {formatted_time}</div>'
        except:
            last_verified_html = f'<div class="last-verified">Last verified: {last_verified}</div>'
    
    # Build the card HTML
    card_html = f"""
    <div class="module-card">
        <div class="module-header">
            <div>
                <div class="module-title">{module_id}</div>
                <div class="module-path">{module_data.get('path', '')}</div>
            </div>
            <div class="module-type">{module_data.get('type', '')}</div>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <div class="compliance-badge {status_class}">{status.replace('_', ' ').title()}</div>
            <div style="font-weight: bold;">{int(compliance_level * 100)}% Compliant</div>
        </div>
        {methods_html}
        {issues_html}
        {last_verified_html}
    </div>
    """
    
    return card_html

def generate_compliance_test_file(output_path):
    """
    Generate a compliance test file template
    
    Args:
        output_path: Path to save the test file
    """
    test_content = """import os
import sys
import unittest
import importlib.util
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgharmonicComplianceTest(unittest.TestCase):
    \"\"\"Tests for Agharmonic Law compliance in modules\"\"\"
    
    def _import_module(self, module_path):
        \"\"\"Import a module from file path\"\"\"
        module_name = Path(module_path).stem
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    
    def _get_module_classes(self, module):
        \"\"\"Get all classes defined in a module\"\"\"
        return [obj for name, obj in module.__dict__.items() 
                if isinstance(obj, type) and obj.__module__ == module.__name__]
    
    def _test_module_complian
(Content truncated due to size limit. Use line ranges to read in chunks)"""