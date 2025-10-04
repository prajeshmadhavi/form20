#!/usr/bin/env python3
"""
Update tracking.json with actual current status by checking existing JSON files
"""
import json
from pathlib import Path

def update_tracking_status():
    """Update tracking.json based on actual JSON file existence"""

    try:
        with open('tracking.json', 'r') as f:
            tracking_data = json.load(f)

        print("Updating tracking status based on actual JSON files...")

        updated_count = 0
        for pdf_record in tracking_data['pdfs']:
            ac_number = pdf_record['ac_number']
            json_path = Path(f"parsedData/AC_{ac_number:03d}.json")
            json_path_alt = Path(f"parsedData/AC_{ac_number}.json")

            # Check both possible formats
            json_exists = json_path.exists() or json_path_alt.exists()

            # Update record
            old_status = pdf_record['status']
            pdf_record['json_exists'] = json_exists
            pdf_record['status'] = 'completed' if json_exists else 'pending'

            if old_status != pdf_record['status']:
                updated_count += 1
                print(f"Updated AC_{ac_number}: {old_status} -> {pdf_record['status']}")

        # Recalculate summary
        completed = sum(1 for p in tracking_data['pdfs'] if p['status'] == 'completed')
        pending = len(tracking_data['pdfs']) - completed

        tracking_data['summary']['completed'] = completed
        tracking_data['summary']['pending'] = pending
        tracking_data['summary']['last_updated'] = '2024-09-25T21:20:00Z'

        # Save updated data
        with open('tracking.json', 'w') as f:
            json.dump(tracking_data, f, indent=2)

        print(f"\n✅ Updated {updated_count} records")
        print(f"📊 Current status:")
        print(f"   Total: {tracking_data['summary']['total_pdfs']}")
        print(f"   Completed: {completed}")
        print(f"   Pending: {pending}")
        print(f"   Type 1: {tracking_data['summary']['type1_count']}")
        print(f"   Type 2: {tracking_data['summary']['type2_count']}")
        print(f"   Type 3: {tracking_data['summary']['type3_count']}")

    except Exception as e:
        print(f"Error updating tracking: {e}")

if __name__ == "__main__":
    update_tracking_status()