#!/usr/bin/env python3
"""
Failed PDF Processor - Text-based extraction for failed PDFs
Uses pdfplumber and intelligent parsing to extract Form 20 data
"""
import json
import csv
import sys
import re
from pathlib import Path
from datetime import datetime
import pdfplumber
import time

class FailedPDFProcessor:
    def __init__(self, csv_file='failed_and_pending_acs.csv'):
        self.csv_file = csv_file
        self.output_dir = Path('parsedData')
        self.output_dir.mkdir(exist_ok=True)
        self.log_dir = Path('failed_pdf_logs')
        self.log_dir.mkdir(exist_ok=True)

    def load_pending_items(self):
        """Load pending items from CSV"""
        pending_items = []
        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Processing Status'] == 'pending':
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

        with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['AC Number', 'Constituency Name', 'District', 'Status', 'PDF Path', 'Processing Status', 'Remarks']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def extract_number(self, text):
        """Extract number from text"""
        if not text:
            return None
        match = re.search(r'\d+', str(text).replace(',', ''))
        return int(match.group()) if match else None

    def parse_table_with_pdfplumber(self, pdf_path):
        """Extract table data using pdfplumber"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                all_tables = []
                total_pages = len(pdf.pages)

                print(f"📄 PDF has {total_pages} pages")

                # Process all pages except last 2 (summary pages)
                pages_to_process = min(total_pages - 2, total_pages) if total_pages > 2 else total_pages

                for page_num in range(pages_to_process):
                    page = pdf.pages[page_num]
                    print(f"📑 Processing page {page_num + 1}/{pages_to_process}")

                    # Extract tables
                    tables = page.extract_tables()
                    if tables:
                        print(f"   Found {len(tables)} tables on page {page_num + 1}")
                        all_tables.extend(tables)

                return all_tables
        except Exception as e:
            print(f"❌ Error extracting tables: {e}")
            return []

    def parse_form20_data(self, tables, ac_number, constituency_name):
        """Parse Form 20 data from extracted tables"""
        result = {
            "Constituency Number": ac_number,
            "constituency_name": constituency_name,
            "Total Number of Electors": None,
            "serial_no_wise_details": [],
            "candidates": [],
            "candidate_names": [],
            "extraction_method": "pdfplumber_text",
            "extraction_timestamp": datetime.now().isoformat()
        }

        if not tables:
            return result

        # Try to find the main data table
        for table_idx, table in enumerate(tables):
            if not table or len(table) < 2:
                continue

            print(f"📊 Analyzing table {table_idx + 1} (rows: {len(table)})")

            # Look for header row with candidate names
            header_row = None
            data_start_idx = None

            for i, row in enumerate(table):
                if not row:
                    continue

                # Check if this is a header row (contains "Serial" or candidate names)
                row_text = ' '.join([str(cell) for cell in row if cell])
                if 'Serial' in row_text or 'Polling Station' in row_text:
                    header_row = row
                    data_start_idx = i + 1
                    print(f"   Found header at row {i}")
                    break

            if not header_row or not data_start_idx:
                continue

            # Extract candidate names from header
            candidate_names = []
            for cell in header_row:
                if cell and cell not in ['Serial', 'Polling', 'Station', 'No.', 'Valid', 'Rejected', 'NOTA', 'Total', 'Tender']:
                    cell_text = str(cell).strip()
                    if len(cell_text) > 3 and not cell_text.isdigit():
                        candidate_names.append(cell_text)

            if candidate_names:
                print(f"   ✅ Found {len(candidate_names)} candidates")
                result["candidates"] = [{"candidate_name": name} for name in candidate_names]
                result["candidate_names"] = candidate_names

            # Extract polling station data
            for row_idx in range(data_start_idx, len(table)):
                row = table[row_idx]
                if not row or len(row) < 3:
                    continue

                # Try to extract serial number (first column)
                serial_no = self.extract_number(row[0])
                if not serial_no:
                    continue

                # Extract vote counts for each candidate
                candidate_votes = []
                valid_votes = 0

                # Try to extract numeric values from row
                for cell in row[1:]:
                    num = self.extract_number(cell)
                    if num is not None:
                        candidate_votes.append(num)
                        valid_votes += num

                # Create polling station entry
                if candidate_votes:
                    station_data = {
                        "Serial No. Of Polling Station": serial_no,
                        "candidate_votes": candidate_votes[:len(candidate_names)] if candidate_names else candidate_votes,
                        "Total Number of valid votes": valid_votes,
                        "Number of Rejected votes": 0,
                        "NOTA": 0,
                        "Total": valid_votes,
                        "Number Of Tender Votes": 0
                    }
                    result["serial_no_wise_details"].append(station_data)

        print(f"📊 Extracted {len(result['serial_no_wise_details'])} polling stations")
        return result

    def process_pdf(self, ac_number, constituency_name, pdf_path):
        """Process a single PDF file"""
        log_file = self.log_dir / f"AC_{ac_number}_processing.log"

        print(f"\n{'='*80}")
        print(f"PROCESSING AC_{ac_number} - {constituency_name}")
        print(f"{'='*80}")
        print(f"📁 PDF Path: {pdf_path}")

        start_time = time.time()

        try:
            # Check if PDF exists
            if not Path(pdf_path).exists():
                raise FileNotFoundError(f"PDF not found: {pdf_path}")

            # Extract tables using pdfplumber
            print(f"🔍 Extracting tables with pdfplumber...")
            tables = self.parse_table_with_pdfplumber(pdf_path)

            if not tables:
                raise ValueError("No tables found in PDF")

            # Parse Form 20 data
            print(f"📊 Parsing Form 20 data...")
            result = self.parse_form20_data(tables, ac_number, constituency_name)

            # Calculate summary statistics
            if result["serial_no_wise_details"]:
                # Find elected person (candidate with most votes)
                candidate_totals = [0] * len(result.get("candidate_names", []))
                for station in result["serial_no_wise_details"]:
                    votes = station.get("candidate_votes", [])
                    for i, vote_count in enumerate(votes):
                        if i < len(candidate_totals):
                            candidate_totals[i] += vote_count

                if candidate_totals and result.get("candidate_names"):
                    max_votes = max(candidate_totals)
                    elected_idx = candidate_totals.index(max_votes)
                    result["Elected Person Name"] = result["candidate_names"][elected_idx]
                    result["elected_person_votes"] = max_votes

            # Save result
            output_file = self.output_dir / f"AC_{ac_number}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            elapsed_time = time.time() - start_time

            print(f"✅ Successfully processed AC_{ac_number}")
            print(f"   Polling Stations: {len(result['serial_no_wise_details'])}")
            print(f"   Candidates: {len(result.get('candidates', []))}")
            print(f"   Time: {elapsed_time:.1f}s")
            print(f"💾 Saved: {output_file}")

            # Update CSV status
            remarks = f"Extracted {len(result['serial_no_wise_details'])} stations, {len(result.get('candidates', []))} candidates"
            self.update_csv_status(ac_number, 'completed', remarks)

            return True

        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = str(e)

            print(f"❌ Failed to process AC_{ac_number}: {error_msg}")
            print(f"   Time: {elapsed_time:.1f}s")

            # Update CSV status
            self.update_csv_status(ac_number, 'failed', f"Error: {error_msg[:100]}")

            # Write detailed log
            with open(log_file, 'w') as f:
                f.write(f"AC_{ac_number} Processing Failed\n")
                f.write(f"{'='*80}\n")
                f.write(f"Error: {error_msg}\n")
                f.write(f"Time: {elapsed_time:.1f}s\n")

            return False

    def process_all_pending(self):
        """Process all pending items from CSV"""
        pending_items = self.load_pending_items()

        print(f"\n{'='*80}")
        print(f"FAILED PDF BATCH PROCESSOR")
        print(f"{'='*80}")
        print(f"Total pending items: {len(pending_items)}")
        print(f"{'='*80}\n")

        completed = 0
        failed = 0

        for idx, item in enumerate(pending_items, 1):
            ac_number = int(item['AC Number'])
            constituency_name = item['Constituency Name']
            pdf_path = item['PDF Path']

            print(f"\n[{idx}/{len(pending_items)}] Processing AC_{ac_number}...")

            success = self.process_pdf(ac_number, constituency_name, pdf_path)

            if success:
                completed += 1
            else:
                failed += 1

            # Small delay between processing
            time.sleep(1)

        print(f"\n{'='*80}")
        print(f"BATCH PROCESSING COMPLETE")
        print(f"{'='*80}")
        print(f"✅ Completed: {completed}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Total: {len(pending_items)}")
        print(f"{'='*80}\n")

def main():
    processor = FailedPDFProcessor()

    if len(sys.argv) > 1:
        # Process single AC
        try:
            ac_number = int(sys.argv[1])
            pending_items = processor.load_pending_items()

            # Find the item
            item = None
            for pending_item in pending_items:
                if int(pending_item['AC Number']) == ac_number:
                    item = pending_item
                    break

            if item:
                success = processor.process_pdf(
                    ac_number,
                    item['Constituency Name'],
                    item['PDF Path']
                )
                sys.exit(0 if success else 1)
            else:
                print(f"❌ AC_{ac_number} not found in pending list")
                sys.exit(1)
        except ValueError:
            print("Usage: python failed_pdf_processor.py [AC_NUMBER]")
            sys.exit(1)
    else:
        # Process all pending
        processor.process_all_pending()

if __name__ == "__main__":
    main()
