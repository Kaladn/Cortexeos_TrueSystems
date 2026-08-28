#!/usr/bin/env python3
"""
UI Element Analyzer for Clearbox AI Contextual Help System

Parses HTML files, identifies all interactive elements, and generates
an editable table for help content authoring.

Usage:
    python ui_analyzer.py <html_file> [--output <output_file>]
    python ui_analyzer.py --dir <directory> [--output <output_file>]
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    print("Error: beautifulsoup4 not installed. Run: pip install beautifulsoup4", file=sys.stderr)


# Interactive element types and their typical selectors
INTERACTIVE_ELEMENTS = {
    'button': ['button', '[role="button"]', '.btn', '.button'],
    'input': ['input', 'textarea'],
    'slider': ['input[type="range"]', '.slider', '[role="slider"]'],
    'dropdown': ['select', '.dropdown', '[role="listbox"]'],
    'toggle': ['input[type="checkbox"]', '.toggle', '[role="switch"]'],
    'link': ['a', '[role="link"]'],
    'tab': ['[role="tab"]', '.tab'],
    'panel': ['.panel', '[role="tabpanel"]', '.section'],
    'card': ['.card', '.item-card'],
    'badge': ['.badge', '.tag'],
    'nav': ['nav', '[role="navigation"]', '.nav-item'],
}

# Priority keywords for automatic classification
PRIORITY_KEYWORDS = {
    'critical': ['send', 'submit', 'run', 'connect', 'save', 'apply', 'start', 'execute', 'prompt', 'temperature', 'model'],
    'important': ['preset', 'toggle', 'select', 'search', 'filter', 'clear', 'reset', 'status', 'navigation'],
    'nice_to_have': ['advanced', 'settings', 'preference', 'theme', 'layout'],
    'optional': ['debug', 'test', 'experimental', 'beta']
}


class UIElement:
    """Represents a single UI element for help system documentation."""
    
    def __init__(self, tag, parent_context="Unknown"):
        self.tag = tag
        self.parent_context = parent_context
        self.help_id = ""
        self.element_type = ""
        self.selector = ""
        self.label = ""
        self.interaction_type = ""
        self.help_status = "❌ Missing"
        self.priority = "🟢 Nice-to-have"
        self.notes = ""
        
        self._analyze()
    
    def _analyze(self):
        """Analyze the tag and extract relevant information."""
        # Determine element type
        self.element_type = self._determine_element_type()
        
        # Generate selector
        self.selector = self._generate_selector()
        
        # Extract label
        self.label = self._extract_label()
        
        # Determine interaction type
        self.interaction_type = self._determine_interaction_type()
        
        # Check for existing help ID
        self._check_help_status()
        
        # Generate help ID suggestion
        self.help_id = self._generate_help_id()
        
        # Assign priority
        self.priority = self._assign_priority()
        
        # Add notes
        self.notes = self._generate_notes()
    
    def _determine_element_type(self) -> str:
        """Determine the type of UI element."""
        tag_name = self.tag.name.lower()
        
        # Check by tag name
        if tag_name == 'button':
            return 'button'
        elif tag_name in ['input', 'textarea']:
            input_type = self.tag.get('type', 'text')
            if input_type == 'range':
                return 'slider'
            elif input_type == 'checkbox':
                return 'toggle'
            elif input_type == 'file':
                return 'file input'
            else:
                return f'input ({input_type})'
        elif tag_name == 'select':
            return 'dropdown'
        elif tag_name == 'a':
            return 'link'
        elif tag_name in ['div', 'section', 'aside']:
            # Check classes for more specific type
            classes = ' '.join(self.tag.get('class', []))
            if 'panel' in classes:
                return 'panel'
            elif 'card' in classes:
                return 'card'
            elif 'badge' in classes or 'tag' in classes:
                return 'badge'
            elif 'slider' in classes:
                return 'slider'
            elif 'toggle' in classes:
                return 'toggle'
            else:
                return 'container'
        
        # Check role attribute
        role = self.tag.get('role')
        if role:
            return f'{role}'
        
        return tag_name
    
    def _generate_selector(self) -> str:
        """Generate a CSS selector for this element."""
        # Prefer ID
        elem_id = self.tag.get('id')
        if elem_id:
            return f'#{elem_id}'
        
        # Use class if available
        classes = self.tag.get('class', [])
        if classes:
            # Use first meaningful class
            for cls in classes:
                if not cls.startswith('_') and len(cls) > 2:
                    return f'.{cls}'
        
        # Use data attributes
        for attr in self.tag.attrs:
            if attr.startswith('data-'):
                return f'[{attr}="{self.tag[attr]}"]'
        
        # Fallback to tag name
        return self.tag.name
    
    def _extract_label(self) -> str:
        """Extract visible label or text content."""
        # Check aria-label
        aria_label = self.tag.get('aria-label')
        if aria_label:
            return aria_label
        
        # Check title
        title = self.tag.get('title')
        if title:
            return title
        
        # Check placeholder for inputs
        placeholder = self.tag.get('placeholder')
        if placeholder:
            return f'[{placeholder}]'
        
        # Get text content
        text = self.tag.get_text(strip=True)
        if text and len(text) < 100:  # Avoid huge text blocks
            return text
        
        # Check for label element
        elem_id = self.tag.get('id')
        if elem_id:
            label = self.tag.find_previous('label', {'for': elem_id})
            if label:
                return label.get_text(strip=True)
        
        # Check for icon classes
        classes = ' '.join(self.tag.get('class', []))
        if 'icon' in classes or 'fa-' in classes:
            return '[icon]'
        
        return '[no visible text]'
    
    def _determine_interaction_type(self) -> str:
        """Determine how users interact with this element."""
        elem_type = self.element_type.lower()
        
        if 'button' in elem_type or 'link' in elem_type:
            return 'click'
        elif 'slider' in elem_type:
            return 'drag'
        elif 'input' in elem_type or 'textarea' in elem_type:
            return 'type'
        elif 'dropdown' in elem_type or 'select' in elem_type:
            return 'select'
        elif 'toggle' in elem_type or 'checkbox' in elem_type:
            return 'toggle'
        elif 'panel' in elem_type:
            return 'click (to open)'
        else:
            return 'interact'
    
    def _check_help_status(self):
        """Check if element has data-help-id attribute."""
        help_id = self.tag.get('data-help-id')
        if help_id:
            self.help_status = '✅ Present'
            self.help_id = help_id
        else:
            self.help_status = '❌ Missing'
    
    def _generate_help_id(self) -> str:
        """Generate a suggested help ID if missing."""
        if self.help_status == '✅ Present':
            return self.help_id
        
        # Use existing ID if available
        elem_id = self.tag.get('id')
        if elem_id:
            # Convert to kebab-case and add context
            clean_id = elem_id.lower().replace('_', '-')
            context = self._infer_context()
            if context and not clean_id.startswith(context):
                return f'{context}.{clean_id}'
            return clean_id
        
        # Generate from label and context
        context = self._infer_context()
        label = self.label.lower()
        label = re.sub(r'[^\w\s-]', '', label)
        label = re.sub(r'\s+', '-', label)
        label = label[:30]  # Limit length
        
        if context:
            return f'{context}.{label}'
        return label
    
    def _infer_context(self) -> str:
        """Infer the parent context from DOM hierarchy."""
        # Check parent elements for context clues
        parent = self.tag.parent
        while parent:
            parent_id = parent.get('id', '')
            parent_classes = ' '.join(parent.get('class', []))
            
            # Check for panel identifiers
            if 'panel' in parent_id or 'panel' in parent_classes:
                # Extract panel name
                if parent_id:
                    return parent_id.replace('panel-', '').replace('_', '-')
                for cls in parent.get('class', []):
                    if 'panel' in cls:
                        return cls.replace('panel-', '')
            
            # Check for section identifiers
            if parent.name in ['section', 'aside', 'nav']:
                if parent_id:
                    return parent_id.replace('_', '-')
            
            parent = parent.parent
        
        return self.parent_context.lower().replace(' ', '-')
    
    def _assign_priority(self) -> str:
        """Assign priority based on element characteristics."""
        label_lower = self.label.lower()
        elem_type = self.element_type.lower()
        
        # Check critical keywords
        for keyword in PRIORITY_KEYWORDS['critical']:
            if keyword in label_lower or keyword in elem_type:
                return '🔴 Critical'
        
        # Check important keywords
        for keyword in PRIORITY_KEYWORDS['important']:
            if keyword in label_lower or keyword in elem_type:
                return '🟡 Important'
        
        # Check optional keywords
        for keyword in PRIORITY_KEYWORDS['optional']:
            if keyword in label_lower:
                return '⚪ Optional'
        
        # Default to nice-to-have
        return '🟢 Nice-to-have'
    
    def _generate_notes(self) -> str:
        """Generate notes about this element."""
        notes = []
        
        # Check for missing labels
        if self.label == '[no visible text]' and self.element_type in ['button', 'link']:
            notes.append('Missing aria-label')
        
        # Check for conditional visibility
        style = self.tag.get('style', '')
        if 'display: none' in style or 'visibility: hidden' in style:
            notes.append('Initially hidden')
        
        # Check for dynamic content
        if self.tag.get('data-dynamic') or 'dynamic' in ' '.join(self.tag.get('class', [])):
            notes.append('Dynamic content')
        
        return '; '.join(notes) if notes else ''
    
    def to_row(self) -> List[str]:
        """Convert to table row."""
        return [
            self.help_id,
            self.element_type,
            self.selector,
            self.label,
            self.parent_context,
            self.interaction_type,
            self.help_status,
            self.priority,
            self.notes
        ]


def analyze_html(html_content: str, filename: str = "unknown") -> List[UIElement]:
    """Analyze HTML content and extract UI elements."""
    if not HAS_BS4:
        return []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    elements = []
    
    # Find all interactive elements
    for selector_type, selectors in INTERACTIVE_ELEMENTS.items():
        for selector in selectors:
            found = soup.select(selector)
            for tag in found:
                # Determine parent context
                parent_context = _find_parent_context(tag)
                element = UIElement(tag, parent_context)
                elements.append(element)
    
    return elements


def _find_parent_context(tag) -> str:
    """Find the parent context (panel/section) for a tag."""
    parent = tag.parent
    while parent:
        parent_id = parent.get('id', '')
        parent_classes = ' '.join(parent.get('class', []))
        
        # Check for panel
        if 'panel' in parent_id:
            return parent_id.replace('panel-', '').replace('_', ' ').title()
        
        # Check for section with meaningful ID
        if parent.name in ['section', 'aside'] and parent_id:
            return parent_id.replace('_', ' ').replace('-', ' ').title()
        
        # Check for nav
        if parent.name == 'nav':
            return 'Navigation'
        
        parent = parent.parent
    
    return 'Unknown'


def generate_markdown_table(elements: List[UIElement]) -> str:
    """Generate Markdown table from elements."""
    if not elements:
        return "No elements found."
    
    # Header
    headers = ['Help ID', 'Element Type', 'Selector', 'Label/Text', 'Parent Context', 
               'Interaction Type', 'Current Help Status', 'Priority', 'Notes']
    
    # Build table
    lines = []
    lines.append('| ' + ' | '.join(headers) + ' |')
    lines.append('|' + '|'.join(['---------|'] * len(headers)))
    
    for elem in elements:
        row = elem.to_row()
        lines.append('| ' + ' | '.join(row) + ' |')
    
    return '\n'.join(lines)


def generate_summary(elements: List[UIElement]) -> str:
    """Generate summary statistics."""
    total = len(elements)
    
    # Count by status
    status_counts = defaultdict(int)
    for elem in elements:
        status_counts[elem.help_status] += 1
    
    # Count by priority
    priority_counts = defaultdict(int)
    for elem in elements:
        priority_counts[elem.priority] += 1
    
    # Count by context
    context_counts = defaultdict(int)
    for elem in elements:
        context_counts[elem.parent_context] += 1
    
    # Build summary
    lines = [
        "## Summary",
        "",
        f"**Total Elements Identified:** {total}",
        "",
        "**By Status:**"
    ]
    
    for status in ['✅ Present', '❌ Missing', '⚠️ Duplicate', '🔍 Needs Review']:
        count = status_counts.get(status, 0)
        lines.append(f"- {status}: {count}")
    
    lines.append("")
    lines.append("**By Priority:**")
    for priority in ['🔴 Critical', '🟡 Important', '🟢 Nice-to-have', '⚪ Optional']:
        count = priority_counts.get(priority, 0)
        lines.append(f"- {priority}: {count}")
    
    lines.append("")
    lines.append("**By Parent Context:**")
    for context, count in sorted(context_counts.items(), key=lambda x: -x[1]):
        lines.append(f"- {context}: {count}")
    
    # Critical gaps
    lines.append("")
    lines.append("**Critical Gaps (Missing Help IDs on Critical Elements):**")
    critical_missing = [e for e in elements if e.priority == '🔴 Critical' and e.help_status == '❌ Missing']
    for i, elem in enumerate(critical_missing[:10], 1):
        lines.append(f"{i}. `{elem.help_id}` — {elem.label}")
    
    return '\n'.join(lines)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze HTML UI and generate help system table",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('html_file', nargs='?', help='HTML file to analyze')
    parser.add_argument('--dir', help='Directory containing HTML files')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    
    args = parser.parse_args()
    
    if not HAS_BS4:
        sys.exit(1)
    
    # Collect HTML files
    html_files = []
    if args.html_file:
        html_files.append(Path(args.html_file))
    elif args.dir:
        html_files = list(Path(args.dir).glob('*.html'))
    else:
        parser.print_help()
        sys.exit(1)
    
    # Analyze all files
    all_elements = []
    for html_file in html_files:
        print(f"Analyzing {html_file}...", file=sys.stderr)
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            elements = analyze_html(content, html_file.name)
            all_elements.extend(elements)
        except Exception as e:
            print(f"Error analyzing {html_file}: {e}", file=sys.stderr)
    
    if not all_elements:
        print("No interactive elements found.", file=sys.stderr)
        sys.exit(1)
    
    # Generate output
    output = []
    output.append("# UI Element Analysis for Contextual Help System")
    output.append("")
    output.append(generate_markdown_table(all_elements))
    output.append("")
    output.append(generate_summary(all_elements))
    
    result = '\n'.join(output)
    
    # Write output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"Analysis written to {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == '__main__':
    main()
