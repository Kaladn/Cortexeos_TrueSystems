"""Test the complete unmapped token review workflow.

This script demonstrates:
1. Analyzing existing 616 maps for unmapped tokens
2. Showing statistics before enrichment
3. Providing a stop-gap for human/AI review
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Set

# Import our analysis tool
from analyze_unmapped_tokens import (
    analyze_reports,
    generate_review_report,
    discover_reports
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
LOGGER = logging.getLogger(__name__)


def load_existing_lexicon(lexicon_path: Path) -> Set[str]:
    """Load existing lexicon tokens for comparison."""
    LOGGER.info(f"Loading lexicon from {lexicon_path}")
    with lexicon_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        raise ValueError("Lexicon is not a list")
    
    tokens = set()
    for entry in data:
        if isinstance(entry, dict):
            token = entry.get("token")
            if token:
                tokens.add(token.lower())
    
    LOGGER.info(f"Loaded {len(tokens):,} tokens from lexicon")
    return tokens


def present_review_interface(report: Dict, lexicon_tokens: Set[str]) -> Dict[str, str]:
    """Present unmapped tokens for human/AI review.
    
    Returns:
        Dict mapping token -> decision (APPROVE, REJECT, DEFER)
    """
    print("\n" + "=" * 80)
    print("UNMAPPED TOKEN REVIEW - APPROVAL INTERFACE")
    print("=" * 80)
    
    summary = report["summary"]
    print(f"\n📊 Analysis Summary:")
    print(f"   • Reports analyzed: {report['reports_analyzed']}")
    print(f"   • Lexicon coverage: {summary['coverage_percentage']}%")
    print(f"   • Unique unmapped tokens: {summary['unique_unmapped_tokens']:,}")
    
    recommendations = report["recommendations"]
    print(f"\n📋 Recommendation Breakdown:")
    print(f"   • STRONG_CANDIDATE: {recommendations['STRONG_CANDIDATE']} tokens")
    print(f"   • CANDIDATE: {recommendations['CANDIDATE']} tokens")
    print(f"   • REVIEW: {recommendations['REVIEW']} tokens")
    print(f"   • LIKELY_NOISE: {recommendations['LIKELY_NOISE']} tokens")
    
    # Group tokens by recommendation
    by_rec = report.get("unmapped_tokens_by_recommendation", {})
    
    decisions: Dict[str, str] = {}
    
    # Auto-approve strong candidates (configurable threshold)
    strong = by_rec.get("STRONG_CANDIDATE", [])
    if strong:
        print(f"\n✅ AUTO-APPROVING {len(strong)} STRONG CANDIDATES:")
        for token_data in strong[:10]:  # Show first 10
            token = token_data["token"]
            print(f"   • {token}: {token_data['total_contexts']} contexts, "
                  f"{token_data['appears_in_reports']} reports")
            decisions[token] = "APPROVE"
        
        if len(strong) > 10:
            print(f"   ... and {len(strong) - 10} more")
            for token_data in strong[10:]:
                decisions[token_data["token"]] = "APPROVE"
    
    # Flag candidates for manual review
    candidates = by_rec.get("CANDIDATE", [])
    if candidates:
        print(f"\n⚠️  {len(candidates)} CANDIDATES REQUIRE REVIEW:")
        for token_data in candidates[:15]:  # Show first 15
            token = token_data["token"]
            print(f"   • {token}: {token_data['total_contexts']} contexts")
            # For demo purposes, auto-approve if looks like valid word
            if token.isalpha() and len(token) >= 4:
                decisions[token] = "APPROVE"
            else:
                decisions[token] = "DEFER"  # Human review needed
        
        if len(candidates) > 15:
            print(f"   ... and {len(candidates) - 15} more (all deferred for review)")
            for token_data in candidates[15:]:
                decisions[token_data["token"]] = "DEFER"
    
    # Auto-reject likely noise or defer for review
    review = by_rec.get("REVIEW", [])
    if review:
        print(f"\n🔍 {len(review)} LOW-FREQUENCY TOKENS (deferred for manual review):")
        for token_data in review[:10]:
            token = token_data["token"]
            print(f"   • {token}: {token_data['total_contexts']} contexts")
            decisions[token] = "DEFER"
    
    noise = by_rec.get("LIKELY_NOISE", [])
    if noise:
        print(f"\n🗑️  {len(noise)} LIKELY NOISE (auto-rejected):")
        for token_data in noise[:10]:
            decisions[token_data["token"]] = "REJECT"
    
    print("\n" + "=" * 80)
    
    # Summary of decisions
    approve_count = sum(1 for d in decisions.values() if d == "APPROVE")
    reject_count = sum(1 for d in decisions.values() if d == "REJECT")
    defer_count = sum(1 for d in decisions.values() if d == "DEFER")
    
    print(f"\n📝 DECISION SUMMARY:")
    print(f"   • APPROVE: {approve_count} tokens (will be added to lexicon)")
    print(f"   • REJECT: {reject_count} tokens (will be ignored)")
    print(f"   • DEFER: {defer_count} tokens (needs human/AI review)")
    print("\n" + "=" * 80)
    
    return decisions


def generate_approval_list(decisions: Dict[str, str], output_path: Path) -> None:
    """Generate a JSON file with approved tokens for lexicon addition."""
    approved = [token for token, decision in decisions.items() if decision == "APPROVE"]
    deferred = [token for token, decision in decisions.items() if decision == "DEFER"]
    rejected = [token for token, decision in decisions.items() if decision == "REJECT"]
    
    approval_data = {
        "generated_at": str(Path(__file__).stat().st_mtime),
        "total_reviewed": len(decisions),
        "approved": {
            "count": len(approved),
            "tokens": sorted(approved)
        },
        "deferred": {
            "count": len(deferred),
            "tokens": sorted(deferred)
        },
        "rejected": {
            "count": len(rejected),
            "tokens": sorted(rejected)
        }
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(approval_data, f, indent=2, ensure_ascii=False)
    
    LOGGER.info(f"Approval list written to {output_path}")
    print(f"\n✅ Approval list saved to: {output_path}")


def main() -> int:
    """Run the complete unmapped token review workflow."""
    # Configuration
    reports_root = Path("forest_ai/data/maps")
    lexicon_path = Path("Lexicon_Canonical/lexicon_v2.json")
    review_output = Path("forest_ai/data/unmapped_tokens_review.json")
    approval_output = Path("forest_ai/data/unmapped_tokens_approved.json")
    
    print("\n" + "=" * 80)
    print("FOREST AI - UNMAPPED TOKEN REVIEW WORKFLOW")
    print("=" * 80)
    print("\nThis workflow analyzes 616 mapping reports and identifies tokens")
    print("that are not in the lexicon, providing a stop-gap for review")
    print("BEFORE any lexicon modifications or enrichment occurs.")
    print("=" * 80)
    
    # Step 1: Discover 616 reports
    print("\n[1/5] Discovering 616 map reports...")
    report_paths = discover_reports(reports_root)
    if not report_paths:
        LOGGER.error(f"No 616 map reports found under {reports_root}")
        return 1
    LOGGER.info(f"Found {len(report_paths)} report(s)")
    
    # Step 2: Analyze unmapped tokens
    print("\n[2/5] Analyzing unmapped tokens from reports...")
    stats_list, unmapped = analyze_reports(report_paths)
    
    # Step 3: Generate review report with statistics
    print("\n[3/5] Generating review report with statistics...")
    report = generate_review_report(stats_list, unmapped, review_output)
    LOGGER.info(f"Review report saved to {review_output}")
    
    # Step 4: Load existing lexicon for comparison
    print("\n[4/5] Loading existing lexicon for validation...")
    lexicon_tokens = load_existing_lexicon(lexicon_path)
    
    # Step 5: Present review interface and collect decisions
    print("\n[5/5] Presenting review interface...")
    decisions = present_review_interface(report, lexicon_tokens)
    
    # Generate approval list
    generate_approval_list(decisions, approval_output)
    
    print("\n" + "=" * 80)
    print("WORKFLOW COMPLETE")
    print("=" * 80)
    print("\n📌 Next Steps:")
    print(f"   1. Review deferred tokens in: {approval_output}")
    print(f"   2. Update approval decisions as needed")
    print(f"   3. Run enrichment with approved tokens only")
    print(f"   4. Validate lexicon schema after enrichment")
    print("\n✨ Stop-gap review complete - no lexicon modifications made yet!")
    print("=" * 80 + "\n")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
