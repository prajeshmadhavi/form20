#!/usr/bin/env python3
"""
Fix JSON file paths in tracking.json to match actual file names in parsedData
"""
import json
import os
from pathlib import Path

def fix_json_paths():
    """Update tracking.json with correct JSON file paths that exist"""

    try:
        with open('tracking.json', 'r') as f:
            tracking_data = json.load(f)

        print("Fixing JSON file paths to match actual files...")

        parsed_dir = Path("parsedData")
        existing_files = set()

        # Get all existing JSON files
        if parsed_dir.exists():
            existing_files = {f.name for f in parsed_dir.glob("*.json")}
            print(f"Found {len(existing_files)} JSON files in parsedData/")

        fixed_count = 0
        missing_count = 0

        for pdf_record in tracking_data['pdfs']:
            ac_number = pdf_record['ac_number']
            old_path = pdf_record['output_json_path']

            # Try different possible file name formats
            possible_names = [
                f"AC_{ac_number}.json",           # AC_1.json
                f"AC_{ac_number:02d}.json",       # AC_01.json
                f"AC_{ac_number:03d}.json"        # AC_001.json
            ]

            # Find which file actually exists
            actual_file = None
            for possible_name in possible_names:
                if possible_name in existing_files:
                    actual_file = possible_name
                    break

            if actual_file:
                new_path = f"parsedData/{actual_file}"
                if old_path != new_path:
                    pdf_record['output_json_path'] = new_path
                    fixed_count += 1

                pdf_record['json_exists'] = True

                if fixed_count <= 5:  # Show first 5 changes
                    print(f"  AC_{ac_number}: {old_path} -> {new_path}")

            else:
                # File doesn't exist
                pdf_record['json_exists'] = False
                missing_count += 1

        # Recalculate summary
        completed = sum(1 for p in tracking_data['pdfs'] if p['json_exists'])
        pending = len(tracking_data['pdfs']) - completed

        tracking_data['summary']['completed'] = completed
        tracking_data['summary']['pending'] = pending
        tracking_data['summary']['last_updated'] = '2024-09-26T01:05:00Z'

        # Save updated data
        with open('tracking.json', 'w') as f:
            json.dump(tracking_data, f, indent=2)

        print(f"\n✅ Fixed {fixed_count} JSON file paths")
        print(f"📄 {completed} PDFs have JSON files")
        print(f"⏳ {missing_count} PDFs missing JSON files")
        print("JSON files will now open correctly in dashboard")

    except Exception as e:
        print(f"Error fixing JSON paths: {e}")

if __name__ == "__main__":
    fix_json_paths()