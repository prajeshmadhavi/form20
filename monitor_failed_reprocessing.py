#!/usr/bin/env python3
"""
Monitor failed PDF reprocessing progress
"""
import csv
import json
from pathlib import Path
from datetime import datetime

def monitor_reprocessing():
    csv_file = 'failed_and_pending_acs.csv'

    # Count statuses
    statuses = {'pending': 0, 'failed': 0, 'completed': 0}

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = row['Processing Status']
            if status in statuses:
                statuses[status] += 1

    total = sum(statuses.values())
    completed_pct = (statuses['completed'] / total * 100) if total > 0 else 0

    print("=" * 60)
    print("FAILED PDF REPROCESSING STATUS")
    print("=" * 60)
    print(f"📊 Progress: {statuses['completed']}/{total} ({completed_pct:.1f}%)")
    print(f"   ✅ Completed: {statuses['completed']}")
    print(f"   ⏳ Pending: {statuses['pending']}")
    print(f"   ❌ Failed: {statuses['failed']}")
    print("=" * 60)

    # Check if any process is running
    import subprocess
    result = subprocess.run(
        ['pgrep', '-f', 'failed_pdf_reprocessor.py'],
        capture_output=True,
        text=True
    )

    if result.stdout.strip():
        print("🔄 Status: RUNNING")
        pids = result.stdout.strip().split('\n')
        print(f"   PIDs: {', '.join(pids)}")
    else:
        print("⏸️  Status: STOPPED")

    print("=" * 60)

    # Show last 10 lines of log
    log_file = Path('failed_reprocess_logs/reprocessing_log.txt')
    if log_file.exists():
        print("\n📋 Recent Log Entries:")
        print("-" * 60)
        with open(log_file, 'r') as f:
            lines = f.readlines()
            for line in lines[-10:]:
                print(line.rstrip())

    print()

if __name__ == "__main__":
    monitor_reprocessing()
