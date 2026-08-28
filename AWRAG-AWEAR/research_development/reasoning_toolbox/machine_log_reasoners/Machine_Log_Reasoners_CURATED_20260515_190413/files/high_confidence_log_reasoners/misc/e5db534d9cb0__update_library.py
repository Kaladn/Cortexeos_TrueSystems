#!/usr/bin/env python3
"""
Library of Defense - Daily Threat Intelligence Update System
Automatically scrapes CVE databases and security advisories to keep defenses current.
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Configuration
LIBRARY_ROOT = Path(__file__).parent.parent
THREAT_INTEL_DIR = LIBRARY_ROOT / "threat_intel" / "daily_updates"
RULES_DIR = LIBRARY_ROOT / "rules"

# Threat intelligence sources
SOURCES = {
    "cve_recent": "https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=20",
    "cyfirma_weekly": "https://www.cyfirma.com/news/weekly-intelligence-report/",
    "trellix_roast": "https://www.trellix.com/blogs/research/dark-web-roast/",
}


def fetch_recent_cves() -> List[Dict]:
    """
    Fetch recent CVEs from NVD API.
    
    Returns:
        List of CVE dictionaries with id, description, severity
    """
    import requests
    
    try:
        response = requests.get(
            SOURCES["cve_recent"],
            headers={"User-Agent": "LibraryOfDefense/1.0"},
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        cves = []
        
        for vuln in data.get("vulnerabilities", []):
            cve = vuln.get("cve", {})
            cve_id = cve.get("id")
            
            descriptions = cve.get("descriptions", [])
            desc = descriptions[0].get("value") if descriptions else "No description"
            
            metrics = cve.get("metrics", {})
            cvss_v3 = metrics.get("cvssMetricV31", [{}])[0]
            severity = cvss_v3.get("cvssData", {}).get("baseSeverity", "UNKNOWN")
            
            cves.append({
                "id": cve_id,
                "description": desc,
                "severity": severity,
                "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}"
            })
        
        return cves
        
    except Exception as e:
        print(f"Error fetching CVEs: {e}")
        return []


def generate_bandit_rule(cve: Dict) -> str:
    """
    Generate a Bandit rule for a CVE if applicable.
    
    Args:
        cve: CVE dictionary
        
    Returns:
        YAML rule string or empty string if not applicable
    """
    desc_lower = cve["description"].lower()
    
    # Pattern matching for common vulnerability types
    if "sql injection" in desc_lower or "sql query" in desc_lower:
        return f"""
# {cve['id']}: SQL Injection
# {cve['description'][:100]}...
# Severity: {cve['severity']}
tests:
  - B608  # hardcoded_sql_expressions
"""
    
    elif "command injection" in desc_lower or "shell" in desc_lower:
        return f"""
# {cve['id']}: Command Injection
# {cve['description'][:100]}...
# Severity: {cve['severity']}
tests:
  - B602  # shell_injection
  - B603  # subprocess_without_shell_equals_true
"""
    
    elif "path traversal" in desc_lower or "directory traversal" in desc_lower:
        return f"""
# {cve['id']}: Path Traversal
# {cve['description'][:100]}...
# Severity: {cve['severity']}
# Custom validation required - see schemas/path_validation.py
"""
    
    return ""


def update_threat_intel():
    """
    Main update function - fetches threat intel and generates rules.
    """
    print("=" * 60)
    print("Library of Defense - Daily Update")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    # Fetch CVEs
    print("Fetching recent CVEs from NVD...")
    cves = fetch_recent_cves()
    print(f"Found {len(cves)} recent CVEs")
    print()
    
    # Filter for HIGH/CRITICAL severity
    critical_cves = [cve for cve in cves if cve["severity"] in ["HIGH", "CRITICAL"]]
    print(f"Critical/High severity: {len(critical_cves)}")
    print()
    
    # Generate daily report
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = THREAT_INTEL_DIR / f"{today}.md"
    
    with open(report_path, "w") as f:
        f.write(f"# Threat Intelligence Update - {today}\n\n")
        f.write(f"**Total CVEs:** {len(cves)}\n")
        f.write(f"**Critical/High:** {len(critical_cves)}\n\n")
        f.write("## Critical Vulnerabilities\n\n")
        
        for cve in critical_cves:
            f.write(f"### {cve['id']} ({cve['severity']})\n\n")
            f.write(f"{cve['description']}\n\n")
            f.write(f"**URL:** {cve['url']}\n\n")
            
            # Generate rule if applicable
            rule = generate_bandit_rule(cve)
            if rule:
                f.write("**Generated Rule:**\n```yaml\n")
                f.write(rule)
                f.write("\n```\n\n")
            
            f.write("---\n\n")
    
    print(f"Report saved: {report_path}")
    print()
    
    # Generate new Bandit rules
    rules_generated = 0
    for cve in critical_cves:
        rule = generate_bandit_rule(cve)
        if rule:
            rule_path = RULES_DIR / "bandit" / f"{cve['id'].lower()}.yaml"
            with open(rule_path, "w") as f:
                f.write(rule)
            rules_generated += 1
    
    print(f"Generated {rules_generated} new Bandit rules")
    print()
    
    # Git commit
    try:
        subprocess.run(["git", "add", "."], cwd=LIBRARY_ROOT, check=True)
        subprocess.run([
            "git", "commit", "-m",
            f"Daily update: {today} - {len(critical_cves)} critical CVEs"
        ], cwd=LIBRARY_ROOT, check=True)
        print("Changes committed to Git")
    except subprocess.CalledProcessError:
        print("No changes to commit")
    
    print()
    print("=" * 60)
    print("Update complete")
    print("=" * 60)


if __name__ == "__main__":
    update_threat_intel()
