#!/usr/bin/env python3
"""
Consolidate duplicate VISION files in completed_1 directory.
Keeps *_COMPLETE_VISION.json files and removes *_VISION.json duplicates.
"""

import os
import json
from pathlib import Path

def consolidate_vision_files(directory):
    """Remove duplicate VISION files, keeping COMPLETE_VISION versions."""

    directory = Path(directory)

    # Find all VISION files
    complete_vision_files = list(directory.glob("AC_*_COMPLETE_VISION.json"))
    vision_files = list(directory.glob("AC_*_VISION.json"))

    print(f"Found {len(complete_vision_files)} COMPLETE_VISION files")
    print(f"Found {len(vision_files)} VISION files")

    removed_count = 0

    # For each COMPLETE_VISION file, check if corresponding VISION file exists
    for complete_file in complete_vision_files:
        # Extract AC number
        ac_num = complete_file.stem.split('_')[1]  # e.g., "2" from "AC_2_COMPLETE_VISION"

        # Check for corresponding VISION file
        vision_file = directory / f"AC_{ac_num}_VISION.json"

        if vision_file.exists():
            print(f"Removing duplicate: {vision_file.name} (keeping {complete_file.name})")
            vision_file.unlink()
            removed_count += 1

    print(f"\nRemoved {removed_count} duplicate VISION files")

    # Summary
    remaining_files = len(list(directory.glob("*.json")))
    print(f"Total JSON files remaining: {remaining_files}")

if __name__ == "__main__":
    directory = "completed_1"

    if not os.path.exists(directory):
        print(f"Error: Directory '{directory}' not found")
        exit(1)

    print(f"Consolidating files in {directory}/\n")
    consolidate_vision_files(directory)
    print("\nConsolidation complete!")
