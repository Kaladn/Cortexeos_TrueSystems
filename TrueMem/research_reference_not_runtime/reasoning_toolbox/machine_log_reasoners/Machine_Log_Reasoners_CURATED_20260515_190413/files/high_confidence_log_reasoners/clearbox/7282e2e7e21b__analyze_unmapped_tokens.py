"""Analyze and review tokens from 616 maps that are not in the lexicon.

This tool extracts tokens marked as `in_lexicon: false` from one or more 616_map.json
files and generates a review list for human/AI approval before enriching the lexicon.
"""
from __future__ import annotations

import argparse
import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from security.data_paths import CHAT_MAPS_DIR

LOGGER = logging.getLogger("analyze_unmapped_tokens")


@dataclass
class UnmappedToken:
    """Represents a token not found in the lexicon during mapping."""
    token: str
    occurrences: int = 0
    total_contexts: int = 0  # Total times it appears in context windows
    appears_in_reports: Set[str] = field(default_factory=set)
    context_samples: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_occurrence(self, report_id: str, context_type: str, distance: str, count: int) -> None:
        """Record an occurrence of this token in a context window."""
        self.occurrences += 1
        self.total_contexts += count
        self.appears_in_reports.add(report_id)
        
        # Keep a sample of contexts (limit to 5)
        if len(self.context_samples) < 5:
            self.context_samples.append({
                "report": report_id,
                "context_type": context_type,
                "distance": distance,
                "count": count
            })
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "token": self.token,
            "occurrences": self.occurrences,
            "total_contexts": self.total_contexts,
            "appears_in_reports": len(self.appears_in_reports),
            "report_ids": sorted(list(self.appears_in_reports)),
            "context_samples": self.context_samples,
            "recommendation": self._get_recommendation()
        }
    
    def _get_recommendation(self) -> str:
        """Provide a recommendation for this token."""
        if self.occurrences >= 10 and self.total_contexts >= 50:
            return "STRONG_CANDIDATE"
        elif self.occurrences >= 5 and self.total_contexts >= 20:
            return "CANDIDATE"
        elif self.occurrences >= 2:
            return "REVIEW"
        else:
            return "LIKELY_NOISE"


@dataclass
class MappingStats:
    """Statistics about a 616 mapping report."""
    report_path: str
    total_tokens: int = 0
    tokens_in_lexicon: int = 0
    tokens_not_in_lexicon: int = 0
    context_entries_analyzed: int = 0
    unmapped_token_names: Set[str] = field(default_factory=set)


def analyze_report(report_path: Path) -> Tuple[MappingStats, Dict[str, UnmappedToken]]:
    """Analyze a single 616 map report for unmapped tokens."""
    stats = MappingStats(report_path=str(report_path))
    unmapped: Dict[str, UnmappedToken] = {}
    
    try:
        with report_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        LOGGER.error(f"Failed to load report {report_path}: {exc}")
        return stats, unmapped
    
    items = data.get("anchors", data.get("items", {}))
    if not isinstance(items, dict):
        LOGGER.warning(f"Report {report_path} has no anchors/items dict")
        return stats, unmapped
    
    report_id = report_path.stem
    
    # Analyze each focus token's context
    for focus_token, focus_data in items.items():
        if not isinstance(focus_data, dict):
            continue
        
        stats.total_tokens += 1
        
        # Check before context
        before = focus_data.get("before", {})
        if isinstance(before, dict):
            for distance, items_list in before.items():
                if not isinstance(items_list, list):
                    continue
                for item in items_list:
                    if not isinstance(item, dict):
                        continue
                    stats.context_entries_analyzed += 1
                    
                    token = item.get("token")
                    in_lexicon = item.get("in_lexicon", True)
                    count = item.get("count", 1)
                    
                    if not in_lexicon and token:
                        stats.tokens_not_in_lexicon += 1
                        stats.unmapped_token_names.add(token)
                        
                        if token not in unmapped:
                            unmapped[token] = UnmappedToken(token=token)
                        unmapped[token].add_occurrence(report_id, "before", str(distance), count)
                    elif in_lexicon:
                        stats.tokens_in_lexicon += 1
        
        # Check after context
        after = focus_data.get("after", {})
        if isinstance(after, dict):
            for distance, items_list in after.items():
                if not isinstance(items_list, list):
                    continue
                for item in items_list:
                    if not isinstance(item, dict):
                        continue
                    stats.context_entries_analyzed += 1
                    
                    token = item.get("token")
                    in_lexicon = item.get("in_lexicon", True)
                    count = item.get("count", 1)
                    
                    if not in_lexicon and token:
                        stats.tokens_not_in_lexicon += 1
                        stats.unmapped_token_names.add(token)
                        
                        if token not in unmapped:
                            unmapped[token] = UnmappedToken(token=token)
                        unmapped[token].add_occurrence(report_id, "after", str(distance), count)
                    elif in_lexicon:
                        stats.tokens_in_lexicon += 1
    
    return stats, unmapped


def analyze_reports(report_paths: List[Path]) -> Tuple[List[MappingStats], Dict[str, UnmappedToken]]:
    """Analyze multiple reports and aggregate unmapped tokens."""
    all_stats: List[MappingStats] = []
    aggregated_unmapped: Dict[str, UnmappedToken] = {}
    
    for report_path in report_paths:
        LOGGER.info(f"Analyzing {report_path}")
        stats, unmapped = analyze_report(report_path)
        all_stats.append(stats)
        
        # Merge unmapped tokens
        for token, data in unmapped.items():
            if token not in aggregated_unmapped:
                aggregated_unmapped[token] = data
            else:
                # Merge occurrences
                existing = aggregated_unmapped[token]
                existing.occurrences += data.occurrences
                existing.total_contexts += data.total_contexts
                existing.appears_in_reports.update(data.appears_in_reports)
                
                # Add more context samples if we have room
                for sample in data.context_samples:
                    if len(existing.context_samples) < 5:
                        existing.context_samples.append(sample)
    
    return all_stats, aggregated_unmapped


def generate_review_report(
    stats_list: List[MappingStats],
    unmapped: Dict[str, UnmappedToken],
    output_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Generate a comprehensive review report."""
    # Aggregate stats
    total_tokens = sum(s.total_tokens for s in stats_list)
    total_in_lexicon = sum(s.tokens_in_lexicon for s in stats_list)
    total_not_in_lexicon = sum(s.tokens_not_in_lexicon for s in stats_list)
    total_context_entries = sum(s.context_entries_analyzed for s in stats_list)
    
    # Sort unmapped tokens by recommendation strength
    sorted_unmapped = sorted(
        unmapped.values(),
        key=lambda x: (
            x._get_recommendation() == "STRONG_CANDIDATE",
            x._get_recommendation() == "CANDIDATE",
            x.total_contexts
        ),
        reverse=True
    )
    
    # Group by recommendation
    by_recommendation: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for token_data in sorted_unmapped:
        recommendation = token_data._get_recommendation()
        by_recommendation[recommendation].append(token_data.to_dict())
    
    report = {
        "analysis_timestamp": str(Path(__file__).stat().st_mtime),
        "reports_analyzed": len(stats_list),
        "summary": {
            "total_focus_tokens": total_tokens,
            "total_context_entries": total_context_entries,
            "context_tokens_in_lexicon": total_in_lexicon,
            "context_tokens_not_in_lexicon": total_not_in_lexicon,
            "unique_unmapped_tokens": len(unmapped),
            "coverage_percentage": round(
                (total_in_lexicon / (total_in_lexicon + total_not_in_lexicon) * 100)
                if (total_in_lexicon + total_not_in_lexicon) > 0 else 0,
                2
            )
        },
        "recommendations": {
            "STRONG_CANDIDATE": len(by_recommendation.get("STRONG_CANDIDATE", [])),
            "CANDIDATE": len(by_recommendation.get("CANDIDATE", [])),
            "REVIEW": len(by_recommendation.get("REVIEW", [])),
            "LIKELY_NOISE": len(by_recommendation.get("LIKELY_NOISE", []))
        },
        "unmapped_tokens_by_recommendation": dict(by_recommendation),
        "per_report_stats": [
            {
                "report": s.report_path,
                "total_tokens": s.total_tokens,
                "tokens_in_lexicon": s.tokens_in_lexicon,
                "tokens_not_in_lexicon": s.tokens_not_in_lexicon,
                "unique_unmapped": len(s.unmapped_token_names)
            }
            for s in stats_list
        ]
    }
    
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        LOGGER.info(f"Review report written to {output_path}")
    
    return report


def print_summary(report: Dict[str, Any]) -> None:
    """Print a human-readable summary to console."""
    summary = report["summary"]
    recs = report["recommendations"]
    
    print("\n" + "=" * 70)
    print("UNMAPPED TOKEN ANALYSIS - SUMMARY")
    print("=" * 70)
    print(f"\nReports Analyzed: {report['reports_analyzed']}")
    print(f"Total Focus Tokens: {summary['total_focus_tokens']:,}")
    print(f"Context Entries Analyzed: {summary['total_context_entries']:,}")
    print(f"\nLexicon Coverage:")
    print(f"  In Lexicon: {summary['context_tokens_in_lexicon']:,}")
    print(f"  NOT in Lexicon: {summary['context_tokens_not_in_lexicon']:,}")
    print(f"  Coverage: {summary['coverage_percentage']}%")
    print(f"\nUnique Unmapped Tokens: {summary['unique_unmapped_tokens']:,}")
    print(f"\nRecommendations:")
    print(f"  STRONG_CANDIDATE: {recs['STRONG_CANDIDATE']:,} tokens (high frequency, add to lexicon)")
    print(f"  CANDIDATE: {recs['CANDIDATE']:,} tokens (moderate frequency, review)")
    print(f"  REVIEW: {recs['REVIEW']:,} tokens (low frequency, manual review)")
    print(f"  LIKELY_NOISE: {recs['LIKELY_NOISE']:,} tokens (very low frequency, likely typos/code)")
    print("\n" + "=" * 70)
    
    # Show top candidates
    strong = report["unmapped_tokens_by_recommendation"].get("STRONG_CANDIDATE", [])
    if strong:
        print("\nTOP STRONG CANDIDATES (first 10):")
        for token_data in strong[:10]:
            print(f"  • {token_data['token']}: "
                  f"{token_data['total_contexts']} contexts, "
                  f"{token_data['appears_in_reports']} reports")
    
    candidates = report["unmapped_tokens_by_recommendation"].get("CANDIDATE", [])
    if candidates:
        print("\nTOP CANDIDATES (first 10):")
        for token_data in candidates[:10]:
            print(f"  • {token_data['token']}: "
                  f"{token_data['total_contexts']} contexts, "
                  f"{token_data['appears_in_reports']} reports")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze unmapped tokens from 616 map reports"
    )
    parser.add_argument(
        "--reports-root",
        type=Path,
        default=CHAT_MAPS_DIR,
        help="Root directory to search for 616_map.json files"
    )
    parser.add_argument(
        "--report",
        action="append",
        type=Path,
        help="Specific report file(s) to analyze"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for JSON review report"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress summary output"
    )
    return parser.parse_args(argv)


def discover_reports(root: Path) -> List[Path]:
    """Find all map_*.json files under root (full anchor data, not metadata-only 616_map.json)."""
    if not root.exists():
        return []
    return sorted(root.glob("map_*.json"))


def main(argv: Optional[List[str]] = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:%(name)s: %(message)s"
    )
    
    args = parse_args(argv)
    
    # Collect report paths
    report_paths: List[Path] = []
    if args.report:
        report_paths.extend(args.report)
    else:
        discovered = discover_reports(args.reports_root)
        report_paths.extend(discovered)
        LOGGER.info(f"Discovered {len(discovered)} report(s) under {args.reports_root}")
    
    if not report_paths:
        LOGGER.error("No reports found to analyze")
        return 1
    
    # Analyze reports
    stats_list, unmapped = analyze_reports(report_paths)
    
    # Generate review report
    output_path = args.output or (CHAT_MAPS_DIR.parent / "unmapped_tokens_review.json")
    report = generate_review_report(stats_list, unmapped, output_path)
    
    # Print summary
    if not args.quiet:
        print_summary(report)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
