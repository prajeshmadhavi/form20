#!/usr/bin/env python3
"""
Real-time monitoring script for batch processing
Shows current progress, statistics, and estimated completion time
"""
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
import os

TRACKING_FILE = "batch_processing_tracking.json"

def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

def load_tracking():
    """Load tracking data"""
    if Path(TRACKING_FILE).exists():
        with open(TRACKING_FILE, 'r') as f:
            return json.load(f)
    return None

def format_time(seconds):
    """Format seconds into human readable time"""
    return str(timedelta(seconds=int(seconds)))

def display_progress():
    """Display current progress"""
    data = load_tracking()

    if not data:
        print("❌ No tracking data found. Batch processing not started yet.")
        return

    clear_screen()

    print("="*80)
    print(" "*20 + "BATCH PROCESSING MONITOR")
    print("="*80)
    print()

    # Current status
    current_ac = data.get("in_progress")
    if current_ac:
        print(f"🔄 CURRENTLY PROCESSING: AC_{current_ac}")
    else:
        print(f"⏸️  STATUS: Idle or between ACs")

    print()

    # Progress statistics
    total = 288
    completed = data.get("total_processed", 0)
    failed = data.get("total_failed", 0)
    skipped = data.get("total_skipped", 0)
    remaining = total - completed - failed - skipped

    progress_pct = (completed / total * 100) if total > 0 else 0

    print(f"📊 PROGRESS: {completed}/{total} ({progress_pct:.1f}%)")
    print()

    # Progress bar
    bar_length = 50
    filled = int(bar_length * progress_pct / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"[{bar}] {progress_pct:.1f}%")
    print()

    # Counts
    print(f"✅ Completed: {completed}")
    print(f"❌ Failed: {failed}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"⏳ Remaining: {remaining}")
    print()

    # Statistics
    stats = data.get("statistics", {})
    total_stations = stats.get("total_polling_stations", 0)
    total_api_calls = stats.get("total_api_calls", 0)
    total_time = stats.get("total_processing_time", 0)

    print(f"📈 STATISTICS:")
    print(f"   Total Polling Stations Extracted: {total_stations:,}")
    print(f"   Total API Calls Made: {total_api_calls:,}")
    print(f"   Total Processing Time: {format_time(total_time)}")

    if completed > 0:
        avg_time = total_time / completed
        avg_stations = total_stations / completed
        print(f"   Average Time per AC: {format_time(avg_time)}")
        print(f"   Average Stations per AC: {avg_stations:.0f}")

    print()

    # Time estimates
    start_time_str = data.get("start_time")
    if start_time_str:
        start_time = datetime.fromisoformat(start_time_str)
        elapsed = datetime.now() - start_time
        print(f"⏱️  TIME:")
        print(f"   Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Elapsed: {format_time(elapsed.total_seconds())}")

        if completed > 0:
            avg_per_ac = elapsed.total_seconds() / completed
            estimated_remaining = avg_per_ac * remaining
            estimated_completion = datetime.now() + timedelta(seconds=estimated_remaining)

            print(f"   Estimated Remaining: {format_time(estimated_remaining)}")
            print(f"   Estimated Completion: {estimated_completion.strftime('%Y-%m-%d %H:%M:%S')}")

    print()

    # Recent activity
    completed_list = data.get("completed", [])
    failed_list = data.get("failed", [])

    if completed_list:
        recent_completed = sorted(completed_list)[-5:]
        print(f"✅ Recently Completed: {', '.join([f'AC_{ac}' for ac in recent_completed])}")

    if failed_list:
        print(f"❌ Failed ACs: {', '.join([f'AC_{ac}' for ac in sorted(failed_list)])}")

    print()
    print("="*80)
    print(f"Last Updated: {data.get('last_updated', 'Unknown')}")
    print("Press Ctrl+C to stop monitoring")
    print("="*80)

def main():
    """Main monitoring loop"""
    print("Starting batch processing monitor...")
    print("Updates every 10 seconds")
    print()

    try:
        while True:
            display_progress()
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")

if __name__ == "__main__":
    main()
