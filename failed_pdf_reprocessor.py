#!/usr/bin/env python3
"""
Failed PDF Reprocessor - Uses fixed Gemini Vision LLM for failed PDFs
Processes all failed PDFs from failed_and_pending_acs.csv
"""
import json
import csv
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

class FailedPDFReprocessor:
    def __init__(self, csv_file='failed_and_pending_acs.csv'):
        self.csv_file = csv_file
        self.output_dir = Path('parsedData')
        self.output_dir.mkdir(exist_ok=True)
        self.log_dir = Path('failed_reprocess_logs')
        self.log_dir.mkdir(exist_ok=True)
        self.processing_log = self.log_dir / 'reprocessing_log.txt'

    def load_pending_items(self):
        """Load pending items from CSV"""
        pending_items = []
        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Processing Status'] in ['pending', 'failed']:
                    pending_items.append(row)
        return pending_items

    def update_csv_status(self, ac_number, status, remarks):
        """Update processing status in CSV"""
        rows = []
        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        for row in rows:
            if int(row['AC Number']) == ac_number:
                row['Processing Status'] = status
                row['Remarks'] = remarks
                break

        with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['AC Number', 'Constituency Name', 'District', 'Status', 'PDF Path', 'Processing Status', 'Remarks']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def log_message(self, message):
        """Log message to file and console"""
        print(message)
        with open(self.processing_log, 'a') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")

    def process_with_gemini(self, ac_number, constituency_name, pdf_path):
        """Process PDF using Gemini Vision extractor"""
        self.log_message(f"\n{'='*80}")
        self.log_message(f"PROCESSING AC_{ac_number} - {constituency_name}")
        self.log_message(f"{'='*80}")
        self.log_message(f"📁 PDF Path: {pdf_path}")

        start_time = time.time()

        try:
            # Check if PDF exists
            if not Path(pdf_path).exists():
                raise FileNotFoundError(f"PDF not found: {pdf_path}")

            # Run Gemini Vision extractor
            self.log_message(f"🤖 Running Gemini Vision extractor...")

            cmd = [
                'python',
                'gemini_vision_extractor.py',
                str(ac_number)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )

            elapsed_time = time.time() - start_time

            # Check if processing was successful
            output_file = self.output_dir / f"AC_{ac_number}.json"

            if result.returncode == 0 and output_file.exists():
                # Verify JSON file
                with open(output_file, 'r') as f:
                    data = json.load(f)

                num_stations = len(data.get('serial_no_wise_details', []))
                num_candidates = len(data.get('candidates', []))

                self.log_message(f"✅ Successfully processed AC_{ac_number}")
                self.log_message(f"   Polling Stations: {num_stations}")
                self.log_message(f"   Candidates: {num_candidates}")
                self.log_message(f"   Time: {elapsed_time:.1f}s")
                self.log_message(f"💾 Saved: {output_file}")

                # Update CSV status
                remarks = f"Extracted {num_stations} stations, {num_candidates} candidates - Gemini Vision"
                self.update_csv_status(ac_number, 'completed', remarks)

                return True
            else:
                error_msg = result.stderr if result.stderr else "Unknown error"
                raise Exception(error_msg)

        except subprocess.TimeoutExpired:
            elapsed_time = time.time() - start_time
            self.log_message(f"❌ Timeout processing AC_{ac_number} after {elapsed_time:.1f}s")
            self.update_csv_status(ac_number, 'failed', "Timeout after 30 minutes")
            return False

        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = str(e)[:200]

            self.log_message(f"❌ Failed to process AC_{ac_number}: {error_msg}")
            self.log_message(f"   Time: {elapsed_time:.1f}s")

            # Update CSV status
            self.update_csv_status(ac_number, 'failed', f"Error: {error_msg[:100]}")

            return False

    def process_all_pending(self, start_from=None, max_items=None):
        """Process all pending items from CSV"""
        pending_items = self.load_pending_items()

        if start_from:
            # Filter items starting from specific AC number
            pending_items = [item for item in pending_items if int(item['AC Number']) >= start_from]

        if max_items:
            pending_items = pending_items[:max_items]

        self.log_message(f"\n{'='*80}")
        self.log_message(f"FAILED PDF REPROCESSOR (Gemini Vision)")
        self.log_message(f"{'='*80}")
        self.log_message(f"Total items to process: {len(pending_items)}")
        self.log_message(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_message(f"{'='*80}\n")

        completed = 0
        failed = 0

        for idx, item in enumerate(pending_items, 1):
            ac_number = int(item['AC Number'])
            constituency_name = item['Constituency Name']
            pdf_path = item['PDF Path']

            self.log_message(f"\n[{idx}/{len(pending_items)}] Processing AC_{ac_number}...")

            success = self.process_with_gemini(ac_number, constituency_name, pdf_path)

            if success:
                completed += 1
            else:
                failed += 1

            # Progress summary every 10 items
            if idx % 10 == 0:
                self.log_message(f"\n📊 PROGRESS UPDATE:")
                self.log_message(f"   Processed: {idx}/{len(pending_items)}")
                self.log_message(f"   ✅ Completed: {completed}")
                self.log_message(f"   ❌ Failed: {failed}")

            # Small delay between processing
            time.sleep(2)

        self.log_message(f"\n{'='*80}")
        self.log_message(f"BATCH REPROCESSING COMPLETE")
        self.log_message(f"{'='*80}")
        self.log_message(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_message(f"✅ Completed: {completed}")
        self.log_message(f"❌ Failed: {failed}")
        self.log_message(f"📊 Total: {len(pending_items)}")
        self.log_message(f"{'='*80}\n")

        return completed, failed

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Reprocess failed PDFs with Gemini Vision')
    parser.add_argument('--ac', type=int, help='Process single AC number')
    parser.add_argument('--start-from', type=int, help='Start from specific AC number')
    parser.add_argument('--max', type=int, help='Maximum number of items to process')
    parser.add_argument('--all', action='store_true', help='Process all pending items')

    args = parser.parse_args()

    processor = FailedPDFReprocessor()

    if args.ac:
        # Process single AC
        pending_items = processor.load_pending_items()
        item = None
        for pending_item in pending_items:
            if int(pending_item['AC Number']) == args.ac:
                item = pending_item
                break

        if item:
            success = processor.process_with_gemini(
                args.ac,
                item['Constituency Name'],
                item['PDF Path']
            )
            sys.exit(0 if success else 1)
        else:
            print(f"❌ AC_{args.ac} not found in pending list")
            sys.exit(1)

    elif args.all or args.start_from or args.max:
        # Process multiple items
        completed, failed = processor.process_all_pending(
            start_from=args.start_from,
            max_items=args.max
        )
        sys.exit(0 if failed == 0 else 1)

    else:
        parser.print_help()
        print("\nExamples:")
        print("  python failed_pdf_reprocessor.py --ac 18           # Process AC_18")
        print("  python failed_pdf_reprocessor.py --all             # Process all pending")
        print("  python failed_pdf_reprocessor.py --start-from 50   # Start from AC_50")
        print("  python failed_pdf_reprocessor.py --max 10          # Process first 10")

if __name__ == "__main__":
    main()
