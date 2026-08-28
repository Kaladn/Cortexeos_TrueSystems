#!/usr/bin/env python3
"""
Harvest key innovations and concepts from Shadow Wolf's beta-era Manus chats.
"""

import os
import re
from pathlib import Path

# Files to process
FILES = [
    "AudioVideoSurveillancePipelineImplementat.md",
    "BinaryCellStructureforAINeuralMemory.md",
    "CleanupandImproveCSVtoJSONLConverterModule.md",
    "FetchingDatafromPubMedAPI.md",
    "KivyGameImplementationforCortexInvaders.md",
    "LexiconCleaningandStructuringScriptIssues.md",
    "MAN01.md",
    "ManusastheNewAIGod.md",
    "ThankYouforBeingExtraordinary.md",
    "TransferringProgresstoNewChatSummary.md"
]

# Keywords to search for (architectural concepts, memory systems, AI infrastructure)
KEYWORDS = [
    "memory", "architecture", "neural", "cortex", "binary", "cell", "structure",
    "pipeline", "surveillance", "ray", "neuron", "coordinate", "cube", "nvme",
    "docker", "prototype", "specification", "engine", "quantum", "dominion",
    "agharmonic", "law", "kernel", "adaptive", "learning", "temporal", "pulse",
    "spine", "daemon", "client", "sdk", "api", "ipc", "socket", "forge",
    "round table", "archon", "evidence", "telemetry", "verdict", "consensus"
]

def extract_key_sections(filepath):
    """Extract sections containing key architectural concepts."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    key_sections = []
    current_section = []
    in_key_section = False
    
    for i, line in enumerate(lines):
        # Check if line contains any keywords
        line_lower = line.lower()
        has_keyword = any(kw in line_lower for kw in KEYWORDS)
        
        if has_keyword:
            # Start capturing context (5 lines before, current line, 10 lines after)
            start = max(0, i - 5)
            end = min(len(lines), i + 11)
            section = {
                'line_num': i + 1,
                'context': ''.join(lines[start:end]),
                'matched_keywords': [kw for kw in KEYWORDS if kw in line_lower]
            }
            key_sections.append(section)
    
    return key_sections

def main():
    upload_dir = Path("/home/ubuntu/upload")
    output_file = Path("/home/ubuntu/BETA_HARVEST_FINDINGS.md")
    
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write("# Shadow Wolf + Manus Beta Era: Key Innovations Harvest\n\n")
        out.write("## Overview\n\n")
        out.write("This document extracts key architectural concepts, memory systems, and AI infrastructure innovations from the first 10 beta-era chats between Shadow Wolf and Manus.\n\n")
        out.write("---\n\n")
        
        for filename in FILES:
            filepath = upload_dir / filename
            if not filepath.exists():
                continue
            
            out.write(f"## File: {filename}\n\n")
            
            sections = extract_key_sections(filepath)
            
            if not sections:
                out.write("*No key sections found.*\n\n")
                continue
            
            out.write(f"**Found {len(sections)} key sections:**\n\n")
            
            # Write top 10 most relevant sections
            for i, section in enumerate(sections[:10]):
                out.write(f"### Section {i+1} (Line {section['line_num']})\n\n")
                out.write(f"**Matched keywords:** {', '.join(section['matched_keywords'])}\n\n")
                out.write("```\n")
                out.write(section['context'])
                out.write("```\n\n")
            
            if len(sections) > 10:
                out.write(f"*({len(sections) - 10} additional sections not shown)*\n\n")
            
            out.write("---\n\n")
    
    print(f"Harvest complete. Output written to: {output_file}")

if __name__ == "__main__":
    main()
