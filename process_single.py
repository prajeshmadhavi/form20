#!/usr/bin/env python3
"""
Process single PDF with manual override capability
Focused on Type 1 (Standard English Format) PDFs first
"""
import json
import os
import sys
from pathlib import Path

def update_tracking_status(ac_number, status, json_exists=False):
    """Update tracking.json with new status"""
    try:
        with open('tracking.json', 'r') as f:
            tracking_data = json.load(f)

        # Find and update the specific PDF record
        for pdf in tracking_data['pdfs']:
            if pdf['ac_number'] == ac_number:
                pdf['status'] = status
                pdf['json_exists'] = json_exists
                pdf['last_updated'] = '2024-09-25T00:00:00Z'
                break

        # Update summary
        completed = sum(1 for p in tracking_data['pdfs'] if p['status'] == 'completed')
        pending = len(tracking_data['pdfs']) - completed
        tracking_data['summary']['completed'] = completed
        tracking_data['summary']['pending'] = pending

        # Save updated tracking
        with open('tracking.json', 'w') as f:
            json.dump(tracking_data, f, indent=2)

        return True
    except Exception as e:
        print(f"Error updating tracking: {e}")
        return False

def process_type1_pdfs():
    """Process only Type 1 PDFs"""
    try:
        with open('tracking.json', 'r') as f:
            tracking_data = json.load(f)

        # Filter for Type 1 PDFs only
        type1_pdfs = [p for p in tracking_data['pdfs'] if p['pdf_type'] == 1]
        pending_type1 = [p for p in type1_pdfs if p['status'] == 'pending']

        print(f"Found {len(type1_pdfs)} Type 1 PDFs")
        print(f"Pending Type 1 PDFs: {len(pending_type1)}")

        if not pending_type1:
            print("No pending Type 1 PDFs to process!")
            return

        print("\nPending Type 1 PDFs:")
        for i, pdf in enumerate(pending_type1[:10]):  # Show first 10
            print(f"{i+1}. AC_{pdf['ac_number']} - {pdf['district']}")

        return pending_type1

    except Exception as e:
        print(f"Error reading tracking data: {e}")
        return []

def process_single_pdf(ac_number, force_override=False):
    """Process a single PDF by AC number"""
    try:
        # Check if this script exists (process.py)
        if not os.path.exists('process.py'):
            print("Error: process.py script not found!")
            return False

        # Check if JSON already exists
        json_path = Path(f"parsedData/AC_{ac_number}.json")
        if json_path.exists() and not force_override:
            print(f"JSON file AC_{ac_number}.json already exists. Use --force to override.")
            return False

        # Run the processing script
        import subprocess
        result = subprocess.run([
            sys.executable, 'process.py', str(ac_number)
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ Successfully processed AC_{ac_number}")
            update_tracking_status(ac_number, 'completed', True)

            # Show output JSON path for manual verification
            if json_path.exists():
                print(f"📄 Output JSON: {json_path}")
                print(f"🌐 Open in browser: file://{json_path.resolve()}")

            return True
        else:
            print(f"❌ Failed to process AC_{ac_number}")
            print(f"Error: {result.stderr}")
            update_tracking_status(ac_number, 'failed', False)
            return False

    except Exception as e:
        print(f"Error processing AC_{ac_number}: {e}")
        return False

def main():
    """Main function with command line interface"""
    print("Form 20 Single PDF Processor - Type 1 Focus")
    print("=" * 50)

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python process_single.py <AC_NUMBER> [--force]")
        print("  python process_single.py --list-type1")
        print("  python process_single.py --process-all-type1")
        print()

        # Show pending Type 1 PDFs
        pending = process_type1_pdfs()
        if pending:
            print(f"\nNext recommended: python process_single.py {pending[0]['ac_number']}")
        return

    command = sys.argv[1]

    if command == '--list-type1':
        process_type1_pdfs()
        return

    if command == '--process-all-type1':
        print("Processing all Type 1 PDFs...")
        try:
            with open('tracking.json', 'r') as f:
                tracking_data = json.load(f)

            type1_pdfs = [p for p in tracking_data['pdfs'] if p['pdf_type'] == 1 and p['status'] == 'pending']

            for i, pdf in enumerate(type1_pdfs):
                print(f"\nProcessing {i+1}/{len(type1_pdfs)}: AC_{pdf['ac_number']}")
                process_single_pdf(pdf['ac_number'], force_override=True)

                # Ask for continuation after each PDF
                response = input("Continue to next PDF? (y/n/q): ").lower()
                if response == 'q':
                    break
                elif response == 'n':
                    print("Stopping bulk processing.")
                    break
        except Exception as e:
            print(f"Error in bulk processing: {e}")
        return

    # Process single AC number
    try:
        ac_number = int(command)
        force = '--force' in sys.argv

        print(f"Processing AC_{ac_number}...")
        success = process_single_pdf(ac_number, force)

        if success:
            print(f"\n✅ AC_{ac_number} processed successfully!")
            print("💡 You can now manually review the output JSON and provide feedback.")
        else:
            print(f"\n❌ Failed to process AC_{ac_number}")

    except ValueError:
        print(f"Invalid AC number: {command}")

if __name__ == "__main__":
    main()