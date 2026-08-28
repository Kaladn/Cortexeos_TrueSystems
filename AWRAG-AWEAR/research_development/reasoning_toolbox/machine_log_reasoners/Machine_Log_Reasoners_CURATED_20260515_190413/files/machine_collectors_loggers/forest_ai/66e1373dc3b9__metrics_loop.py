"""
Forest AI - Metrics Collection Loop
Background service for tracking system metrics
v1.1.0
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from bridges.forest_database import get_database

def collect_metrics() -> Dict[str, Any]:
    """Collect current system metrics"""
    db = get_database()
    
    # Get statistics
    stats = db.get_statistics()
    
    # Get latest metrics for delta calculation
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    recent_metrics = db.get_metrics_range(str(yesterday), str(today))
    
    # Calculate deltas
    lexicon_delta = 0
    coverage_delta = 0.0
    
    if len(recent_metrics) >= 2:
        lexicon_delta = recent_metrics[-1].get('lexicon_size', 0) - recent_metrics[0].get('lexicon_size', 0)
        coverage_delta = recent_metrics[-1].get('avg_coverage', 0) - recent_metrics[0].get('avg_coverage', 0)
    
    return {
        'timestamp': datetime.now().isoformat(),
        'total_jobs': stats.get('total_jobs', 0),
        'completed_jobs': stats.get('completed_jobs', 0),
        'avg_coverage': stats.get('avg_coverage', 0),
        'approved_tokens': stats.get('approved_tokens', 0),
        'pending_reviews': stats.get('pending_reviews', 0),
        'active_plugins': stats.get('active_plugins', 0),
        'lexicon_delta_24h': lexicon_delta,
        'coverage_delta_24h': coverage_delta
    }

def save_daily_snapshot(metrics: Dict[str, Any]):
    """Save daily metrics snapshot"""
    db = get_database()
    
    # Save to database
    db.save_daily_metrics(
        lexicon_size=metrics.get('approved_tokens', 0),  # Using approved as proxy for lexicon growth
        total_jobs=metrics.get('total_jobs', 0),
        avg_coverage=metrics.get('avg_coverage', 0),
        total_enrichments=metrics.get('approved_tokens', 0),
        new_tokens_approved=metrics.get('lexicon_delta_24h', 0),
        snapshot_data=metrics
    )
    
    # Also save to JSON file
    snapshots_dir = Path("data/snapshots")
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    
    snapshot_file = snapshots_dir / f"metrics_{datetime.now().strftime('%Y%m%d')}.json"
    with open(snapshot_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"[METRICS] Daily snapshot saved: {snapshot_file}")

def check_weekly_snapshot():
    """Check if weekly snapshot is needed"""
    db = get_database()
    
    # Check if it's been a week since last snapshot
    latest = db.get_latest_snapshot()
    
    if latest is None:
        # First snapshot
        create_weekly_snapshot()
        return
    
    last_date = datetime.fromisoformat(latest['created_at']).date()
    today = datetime.now().date()
    
    if (today - last_date).days >= 7:
        create_weekly_snapshot()

def create_weekly_snapshot():
    """Create weekly snapshot"""
    db = get_database()
    
    today = datetime.now().date()
    week_start = today - timedelta(days=7)
    
    # Get metrics for the week
    weekly_metrics = db.get_metrics_range(str(week_start), str(today))
    
    if not weekly_metrics:
        print("[METRICS] No metrics data for weekly snapshot")
        return
    
    # Calculate aggregates
    jobs_count = sum(m.get('total_jobs', 0) for m in weekly_metrics)
    
    # Lexicon growth
    lexicon_start = weekly_metrics[0].get('lexicon_size', 0)
    lexicon_end = weekly_metrics[-1].get('lexicon_size', 0)
    lexicon_growth = lexicon_end - lexicon_start
    
    # Coverage delta
    coverage_start = weekly_metrics[0].get('avg_coverage', 0)
    coverage_end = weekly_metrics[-1].get('avg_coverage', 0)
    coverage_delta = coverage_end - coverage_start
    
    # Get top approved tokens from this week
    approved = db.get_approved_tokens()
    top_tokens = [t['token'] for t in approved[:20]]  # Top 20
    
    # Create snapshot file
    snapshots_dir = Path("data/snapshots")
    snapshot_file = snapshots_dir / f"weekly_{today.strftime('%Y%m%d')}.json"
    
    snapshot_data = {
        'week_start': str(week_start),
        'week_end': str(today),
        'jobs_count': jobs_count,
        'lexicon_growth': lexicon_growth,
        'coverage_delta': coverage_delta,
        'top_tokens': top_tokens,
        'daily_metrics': weekly_metrics
    }
    
    with open(snapshot_file, 'w') as f:
        json.dump(snapshot_data, f, indent=2)
    
    # Save to database
    db.save_weekly_snapshot(
        week_start=str(week_start),
        week_end=str(today),
        jobs_count=jobs_count,
        lexicon_growth=lexicon_growth,
        coverage_delta=coverage_delta,
        top_tokens=top_tokens,
        snapshot_file=str(snapshot_file)
    )
    
    print(f"[METRICS] ✅ Weekly snapshot created: {snapshot_file}")
    print(f"[METRICS]    Jobs: {jobs_count}")
    print(f"[METRICS]    Lexicon Growth: +{lexicon_growth}")
    print(f"[METRICS]    Coverage Delta: {coverage_delta:+.2f}%")

def metrics_loop():
    """Main metrics collection loop"""
    print("[METRICS] Metrics collection loop started")
    print("[METRICS] Collecting daily snapshots at midnight")
    print("[METRICS] Creating weekly snapshots every 7 days")
    
    last_daily_snapshot = None
    
    while True:
        try:
            now = datetime.now()
            
            # Collect metrics every hour
            if now.minute == 0:
                metrics = collect_metrics()
                print(f"[METRICS] Hourly collection: Jobs={metrics['total_jobs']}, "
                      f"Coverage={metrics['avg_coverage']:.1f}%, "
                      f"Approved={metrics['approved_tokens']}")
            
            # Daily snapshot at midnight
            if now.hour == 0 and now.minute == 0:
                today = now.date()
                if last_daily_snapshot != today:
                    metrics = collect_metrics()
                    save_daily_snapshot(metrics)
                    last_daily_snapshot = today
                    
                    # Check if weekly snapshot needed
                    check_weekly_snapshot()
            
            # Sleep for 1 minute
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("[METRICS] Metrics loop stopped")
            break
        except Exception as e:
            print(f"[METRICS] Error in metrics loop: {e}")
            time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    # Initialize database
    db = get_database()
    
    # Collect initial metrics
    print("[METRICS] Collecting initial metrics...")
    initial_metrics = collect_metrics()
    print(json.dumps(initial_metrics, indent=2))
    
    # Start loop
    metrics_loop()
