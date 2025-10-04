#!/usr/bin/env python3
"""
Fix PDF URLs in tracking.json to use HTTP instead of file:// protocol
"""
import json
import os

def fix_pdf_urls():
    """Update tracking.json to use HTTP URLs instead of file:// URLs"""

    try:
        with open('tracking.json', 'r') as f:
            tracking_data = json.load(f)

        print("Fixing PDF URLs from file:// to HTTP...")
        updated_count = 0

        for pdf_record in tracking_data['pdfs']:
            # Current file:// URL
            old_url = pdf_record['chrome_url']

            # Extract relative path from the file URL
            if old_url.startswith('file://'):
                # Remove the base path and keep only the relative part
                relative_path = pdf_record['pdf_path']  # This is already relative like "VIDHANSABHA_2024/..."

                # Create HTTP URL for web server
                new_url = relative_path  # Just the relative path, browser will use current server

                pdf_record['chrome_url'] = new_url
                updated_count += 1

                if updated_count <= 5:  # Show first 5 changes
                    print(f"  AC_{pdf_record['ac_number']}: {old_url} -> {new_url}")

        # Save updated data
        with open('tracking.json', 'w') as f:
            json.dump(tracking_data, f, indent=2)

        print(f"\n✅ Updated {updated_count} PDF URLs")
        print("PDFs will now open via HTTP server instead of file:// protocol")

    except Exception as e:
        print(f"Error fixing PDF URLs: {e}")

if __name__ == "__main__":
    fix_pdf_urls()