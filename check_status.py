#!/usr/bin/env python3
"""Quick status checker for batch processing"""
import json
from pathlib import Path

TRACKING_FILE = "batch_processing_tracking.json"

if not Path(TRACKING_FILE).exists():
    print("❌ Batch processing not started yet")
    print("Run: ./run_batch_persistent.sh")
    exit(0)

with open(TRACKING_FILE, 'r') as f:
    data = json.load(f)

completed = data.get("total_processed", 0)
failed = data.get("total_failed", 0)
skipped = data.get("total_skipped", 0)
current = data.get("in_progress")
total = 288

print(f"\n{'='*60}")
print(f"BATCH PROCESSING STATUS")
print(f"{'='*60}")

if current:
    print(f"🔄 Currently processing: AC_{current}")
else:
    print(f"⏸️  Status: Idle")

print(f"\n📊 Progress: {completed + failed + skipped}/{total}")
print(f"   ✅ Completed: {completed}")
print(f"   ❌ Failed: {failed}")
print(f"   ⏭️  Skipped: {skipped}")
print(f"   ⏳ Remaining: {total - completed - failed - skipped}")

stats = data.get("statistics", {})
print(f"\n📈 Statistics:")
print(f"   Polling Stations: {stats.get('total_polling_stations', 0):,}")
print(f"   API Calls: {stats.get('total_api_calls', 0):,}")
print(f"   Processing Time: {stats.get('total_processing_time', 0)/3600:.2f} hours")

if failed > 0:
    print(f"\n❌ Failed ACs: {sorted(data.get('failed', []))}")

print(f"\n{'='*60}")
print(f"Last updated: {data.get('last_updated', 'Unknown')}")
print(f"{'='*60}\n")
