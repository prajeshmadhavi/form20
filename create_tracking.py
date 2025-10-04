#!/usr/bin/env python3
"""
Create tracking.json for all PDF files with metadata
"""
import json
import os
from pathlib import Path
import re

def get_pdf_type(pdf_path, district):
    """Classify PDF type based on district and format patterns"""

    # Type 1 districts (Standard English Format)
    type1_districts = [
        'Ahmednagar', 'Nagpur', 'Pune', 'Nashik', 'Aurangabad', 'Solapur',
        'Satara', 'Sangli', 'Kolhapur', 'Ratnagiri', 'Sindhudurg', 'Raigad',
        'Thane', 'Palghar', 'Dhule', 'Nandurbar', 'Jalgaon', 'Buldhana',
        'Washim', 'Osmanabad', 'Nanded', 'Latur', 'Parbhani', 'Hingoli',
        'Beed', 'Jalna'
    ]

    # Type 2 districts (Local Language Format)
    type2_districts = [
        'Akola', 'Amravati', 'Yavatmal', 'Wardha', 'Chandrapur', 'Bhandara',
        'Gondia', 'Gadchiroli'
    ]

    # Type 3 districts (Scanned/Image Format)
    type3_districts = [
        'Mumbai_City_District', 'Mumbai_Suburban_District'
    ]

    if district in type1_districts:
        return 1
    elif district in type2_districts:
        return 2
    elif district in type3_districts:
        return 3
    else:
        return 1  # Default to Type 1

def create_tracking_json():
    """Create tracking.json with all PDF records"""

    base_dir = Path("VIDHANSABHA_2024")
    parsed_dir = Path("parsedData")
    tracking_data = []

    print("Scanning for PDF files...")

    # Scan all districts and PDFs
    for district_dir in base_dir.iterdir():
        if district_dir.is_dir():
            district_name = district_dir.name

            for pdf_file in district_dir.glob("*.pdf"):
                # Extract AC number from filename
                match = re.search(r'AC_(\d+)\.pdf', pdf_file.name)
                if not match:
                    continue

                ac_number = match.group(1)

                # Check if output JSON exists
                output_json_path = parsed_dir / f"AC_{ac_number}.json"
                json_exists = output_json_path.exists()

                # Get PDF type
                pdf_type = get_pdf_type(pdf_file, district_name)

                # Create file path for Chrome opening
                chrome_path = f"file://{pdf_file.resolve()}"

                record = {
                    "ac_number": int(ac_number),
                    "pdf_name": pdf_file.name,
                    "district": district_name,
                    "pdf_path": str(pdf_file),
                    "chrome_url": chrome_path,
                    "output_json_path": str(output_json_path),
                    "pdf_type": pdf_type,
                    "pdf_type_description": {
                        1: "Type 1 - Standard English Format",
                        2: "Type 2 - Local Language Format",
                        3: "Type 3 - Scanned/Image Format"
                    }[pdf_type],
                    "status": "completed" if json_exists else "pending",
                    "json_exists": json_exists,
                    "created_timestamp": None,
                    "last_updated": None
                }

                tracking_data.append(record)

    # Sort by AC number
    tracking_data.sort(key=lambda x: x['ac_number'])

    # Create summary statistics
    total_pdfs = len(tracking_data)
    completed_count = sum(1 for r in tracking_data if r['status'] == 'completed')
    pending_count = total_pdfs - completed_count

    type1_count = sum(1 for r in tracking_data if r['pdf_type'] == 1)
    type2_count = sum(1 for r in tracking_data if r['pdf_type'] == 2)
    type3_count = sum(1 for r in tracking_data if r['pdf_type'] == 3)

    summary = {
        "total_pdfs": total_pdfs,
        "completed": completed_count,
        "pending": pending_count,
        "type1_count": type1_count,
        "type2_count": type2_count,
        "type3_count": type3_count,
        "last_updated": "2024-09-25T00:00:00Z"
    }

    # Final structure
    tracking_json = {
        "summary": summary,
        "pdfs": tracking_data
    }

    # Save to tracking.json
    with open("tracking.json", "w") as f:
        json.dump(tracking_json, f, indent=2)

    print(f"Created tracking.json with {total_pdfs} PDF records")
    print(f"Type 1 (Standard): {type1_count}")
    print(f"Type 2 (Local Language): {type2_count}")
    print(f"Type 3 (Scanned): {type3_count}")
    print(f"Completed: {completed_count}")
    print(f"Pending: {pending_count}")

if __name__ == "__main__":
    create_tracking_json()