"""
Data Gathering Monitoring Interface for Kali Ka

This module provides a simple monitoring interface for the automated data gathering system,
allowing users to track progress, view logs, and manage the data gathering process.

Author: Manus
Date: April 8, 2025
"""

import os
import json
import time
import datetime
import glob
from typing import Dict, List, Any, Optional

class DataGatheringMonitor:
    def __init__(self, base_dir="/home/ubuntu/nexus_project"):
        self.base_dir = base_dir
        self.data_dir = f"{base_dir}/data_gathering"
        self.log_dir = f"{self.data_dir}/logs"
        self.raw_dir = f"{self.data_dir}/raw"
        self.processed_dir = f"{self.data_dir}/processed"
        self.validated_dir = f"{self.data_dir}/validated"
        self.kb_dir = f"{base_dir}/knowledge_base/units"
        self.exp_dir = f"{base_dir}/experiential_learning/scenarios"
        
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the data gathering system"""
        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "raw_files": len(glob.glob(f"{self.raw_dir}/*")),
            "processed_files": len(glob.glob(f"{self.processed_dir}/*")),
            "validated_files": len(glob.glob(f"{self.validated_dir}/*")),
            "knowledge_units": len(glob.glob(f"{self.kb_dir}/*")),
            "experiences": len(glob.glob(f"{self.exp_dir}/*")),
            "logs": len(glob.glob(f"{self.log_dir}/*")),
            "latest_report": self._get_latest_report(),
            "latest_logs": self._get_latest_logs(5)
        }
    
    def get_domain_stats(self) -> Dict[str, Dict[str, int]]:
        """Get statistics by domain"""
        domains = ['security', 'ai_ethics', 'computer_science', 'critical_thinking']
        stats = {}
        
        for domain in domains:
            raw_count = len(glob.glob(f"{self.raw_dir}/{domain}_*"))
            processed_count = len(glob.glob(f"{self.processed_dir}/{domain}_*"))
            validated_count = len(glob.glob(f"{self.validated_dir}/{domain}_*"))
            
            # Count knowledge units by domain
            kb_count = 0
            for kb_file in glob.glob(f"{self.kb_dir}/*.json"):
                try:
                    with open(kb_file, 'r') as f:
                        unit = json.load(f)
                        if unit.get('domain') == domain:
                            kb_count += 1
                except:
                    pass
            
            # Count experiences by domain
            exp_count = 0
            for exp_file in glob.glob(f"{self.exp_dir}/*.json"):
                try:
                    with open(exp_file, 'r') as f:
                        exp = json.load(f)
                        if exp.get('domain') == domain:
                            exp_count += 1
                except:
                    pass
            
            stats[domain] = {
                "raw": raw_count,
                "processed": processed_count,
                "validated": validated_count,
                "knowledge_units": kb_count,
                "experiences": exp_count
            }
        
        return stats
    
    def _get_latest_report(self) -> Optional[Dict[str, Any]]:
        """Get the latest data gathering report"""
        report_files = glob.glob(f"{self.data_dir}/data_gathering_report_*.json")
        if not report_files:
            return None
        
        latest_report = max(report_files, key=os.path.getctime)
        try:
            with open(latest_report, 'r') as f:
                return json.load(f)
        except:
            return {"error": "Failed to load report", "file": latest_report}
    
    def _get_latest_logs(self, count=5) -> List[str]:
        """Get the latest log entries"""
        log_files = glob.glob(f"{self.log_dir}/*.log")
        if not log_files:
            return ["No logs found"]
        
        latest_log = max(log_files, key=os.path.getctime)
        try:
            with open(latest_log, 'r') as f:
                lines = f.readlines()
                return lines[-count:] if len(lines) > count else lines
        except:
            return [f"Failed to read log file: {latest_log}"]
    
    def print_status_report(self):
        """Print a formatted status report to console"""
        status = self.get_status()
        domain_stats = self.get_domain_stats()
        
        print("\n" + "="*50)
        print(" KALI KA DATA GATHERING SYSTEM - STATUS REPORT")
        print("="*50)
        print(f"Report Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*50)
        print(f"Raw Data Files:       {status['raw_files']}")
        print(f"Processed Files:      {status['processed_files']}")
        print(f"Validated Files:      {status['validated_files']}")
        print(f"Knowledge Units:      {status['knowledge_units']}")
        print(f"Experience Scenarios: {status['experiences']}")
        print("-"*50)
        print("DOMAIN STATISTICS:")
        
        for domain, stats in domain_stats.items():
            print(f"\n{domain.upper()}:")
            print(f"  Raw Data:         {stats['raw']}")
            print(f"  Processed:        {stats['processed']}")
            print(f"  Validated:        {stats['validated']}")
            print(f"  Knowledge Units:  {stats['knowledge_units']}")
            print(f"  Experiences:      {stats['experiences']}")
        
        print("\n" + "-"*50)
        print("LATEST LOG ENTRIES:")
        for log_entry in status['latest_logs']:
            print(f"  {log_entry.strip()}")
        
        print("="*50 + "\n")

def main():
    """Main function to run the monitor"""
    monitor = DataGatheringMonitor()
    monitor.print_status_report()

if __name__ == "__main__":
    main()
