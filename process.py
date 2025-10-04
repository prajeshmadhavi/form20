#!/usr/bin/env python3
"""
Consolidated Form 20 PDF Extractor
Processes Maharashtra election Form 20 PDFs and extracts data to JSON format.
Automatically detects PDF types (1, 2, 3) and applies appropriate extraction methods.
"""

import sys
import os
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import traceback

# PDF Processing Libraries
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import pymupdf  # For additional PDF handling

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PDFType:
    """PDF Type classifications based on report.md analysis"""
    STANDARD = 1  # Standard English tabular format (easily parseable)
    LOCAL_LANGUAGE = 2  # Mixed English/Marathi format (medium difficulty)
    SCANNED = 3  # Scanned/rotated image format (challenging)


class Form20Extractor:
    """Main extractor class for Form 20 PDFs"""

    def __init__(self, ac_number: int):
        self.ac_number = ac_number
        self.pdf_path = None
        self.output_dir = Path("parsedData")
        self.output_dir.mkdir(exist_ok=True)
        self.json_output_path = self.output_dir / f"AC_{ac_number}.json"
        self.pdf_type = None
        self.data = {}

    def find_pdf(self) -> bool:
        """Find the PDF file for the given AC number in VIDHANSABHA_2024 directory"""
        base_dir = Path("VIDHANSABHA_2024")
        if not base_dir.exists():
            logger.error(f"Directory {base_dir} not found")
            return False

        # Search for AC_XXX.pdf in all subdirectories - try both formats
        patterns = [
            f"AC_{self.ac_number}.pdf",  # AC_1.pdf
            f"AC_{self.ac_number:02d}.pdf"  # AC_01.pdf (with leading zero)
        ]

        for district_dir in base_dir.iterdir():
            if district_dir.is_dir():
                for pdf_pattern in patterns:
                    potential_pdf = district_dir / pdf_pattern
                    if potential_pdf.exists():
                        self.pdf_path = potential_pdf
                        logger.info(f"Found PDF: {self.pdf_path}")
                        return True

        logger.error(f"PDF not found for AC_{self.ac_number} (tried both AC_{self.ac_number}.pdf and AC_{self.ac_number:02d}.pdf)")
        return False

    def check_if_already_processed(self) -> bool:
        """Check if JSON output already exists"""
        if self.json_output_path.exists():
            logger.info(f"Output already exists: {self.json_output_path}, skipping processing")
            return True
        return False

    def detect_pdf_type(self) -> int:
        """Get the PDF type from tracking.json (pre-computed smart classification)"""
        try:
            # Load pre-computed classification from tracking.json
            tracking_file = Path("tracking.json")
            if tracking_file.exists():
                with open(tracking_file, 'r') as f:
                    tracking_data = json.load(f)

                # Find this AC number in the tracking data
                for pdf_record in tracking_data['pdfs']:
                    if pdf_record['ac_number'] == self.ac_number:
                        pdf_type = pdf_record['pdf_type']
                        type_desc = pdf_record['pdf_type_description']
                        logger.info(f"Using pre-computed classification: {type_desc}")
                        return pdf_type

                logger.warning(f"AC_{self.ac_number} not found in tracking.json, falling back to content analysis")

            # Fallback to content analysis if tracking.json not available
            with pdfplumber.open(self.pdf_path) as pdf:
                if not pdf.pages:
                    return PDFType.SCANNED

                first_page = pdf.pages[0]
                text = first_page.extract_text()

                if not text or len(text.strip()) < 100:
                    logger.info("No or minimal text extracted - Type 3 (Scanned/Image)")
                    return PDFType.SCANNED

                # Check for Devanagari script (indicates Type 2)
                devanagari_pattern = r'[\u0900-\u097F]'
                if re.search(devanagari_pattern, text):
                    logger.info("Devanagari script detected - Type 2 (Local Language)")
                    return PDFType.LOCAL_LANGUAGE

                # Check for rotation issues
                # If table extraction fails, might be rotated
                tables = first_page.extract_tables()
                if not tables or len(tables) == 0:
                    logger.info("No tables extracted - possibly Type 3 (Rotated/Scanned)")
                    return PDFType.SCANNED

                logger.info("Standard format detected - Type 1 (Standard English)")
                return PDFType.STANDARD

        except Exception as e:
            logger.error(f"Error detecting PDF type: {e}")
            return PDFType.SCANNED

    def extract_constituency_info(self, text: str) -> Dict:
        """Extract constituency number and name from header"""
        info = {
            'Constituency Number': self.ac_number,
            'Constituency Name': None,
            'Total Number of Electors': None
        }

        # Extract constituency name (e.g., "15 AMALNER")
        pattern = rf'{self.ac_number}[-\s]+([A-Z\s]+)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['Constituency Name'] = match.group(1).strip()

        # Extract total electors - enhanced patterns
        electors_patterns = [
            r'Total No\. of Electors.*?(\d{6,})',
            r'Total.*Electors.*?(\d{6,})',
            r'Electors.*?(\d{6,})',
            r'Assembly Constituency.*?(\d{6,})',
            r'(\d{6,})'  # Any 6+ digit number as fallback
        ]

        for pattern in electors_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                potential_number = int(match.group(1))
                # Use the most likely number (308272 for AC_15)
                if potential_number >= 100000:  # Realistic total electors
                    info['Total Number of Electors'] = potential_number
                    logger.info(f"Found Total Number of Electors: {potential_number}")
                    break

        return info

    def extract_candidates_from_header(self, text: str) -> List[str]:
        """Extract candidate names from the header section"""
        candidates = []

        # Look for the section with candidate names
        # Usually appears after "No of Valid Votes Cast in favour of"
        lines = text.split('\n')
        start_index = -1

        for i, line in enumerate(lines):
            if 'No of Valid Votes Cast in favour of' in line or 'Valid Votes Cast in favour' in line:
                start_index = i
                break

        if start_index != -1 and start_index < len(lines) - 1:
            # Next few lines contain candidate names
            # They're usually in a specific pattern before the data rows start
            for i in range(start_index + 1, min(start_index + 20, len(lines))):
                line = lines[i].strip()
                # Skip common headers and numbers
                if line and not line.isdigit() and len(line) > 2:
                    if not any(skip in line.lower() for skip in ['serial', 'poll', 'total', 'nota', 'rejected', 'tender']):
                        # This might be a candidate name
                        # Clean up the name
                        name_parts = line.split()
                        if name_parts:
                            candidates.extend(name_parts)

        return candidates

    def fix_candidate_name(self, scrambled_name):
        """Fix scrambled candidate name from PDF extraction"""
        if not scrambled_name or not scrambled_name.strip():
            return ''

        # Handle the specific scrambling pattern in AC_15 type PDFs
        words = scrambled_name.split('\n')
        corrected_words = []

        for word in words:
            if word.strip():
                # Reverse characters in each word
                reversed_word = word.strip()[::-1]
                corrected_words.append(reversed_word)

        # Reverse the order of words for proper name sequence
        corrected_words.reverse()

        return ' '.join(corrected_words)

    def extract_type1_standard(self) -> Dict:
        """Extract data from Type 1 (Standard English) PDFs with enhanced candidate extraction"""
        logger.info("Extracting Type 1 (Standard) PDF")

        with pdfplumber.open(self.pdf_path) as pdf:
            full_text = ""
            all_tables = []

            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)

            # Extract constituency info
            constituency_info = self.extract_constituency_info(full_text)

            # Enhanced candidate and polling station data extraction
            serial_no_wise_details = []
            candidate_names = []
            candidate_vote_totals = []

            # Process tables with enhanced logic
            for table_num, table in enumerate(all_tables):
                if not table or len(table) < 2:
                    continue

                # Look for main data table (usually table with most columns)
                if len(table[0]) >= 15:  # Main voting table
                    logger.info(f"Processing main data table {table_num} with {len(table)} rows")

                    # Extract candidate names from row 1 (header row)
                    if len(table) > 1 and not candidate_names:
                        candidate_row = table[1]
                        for col_num in range(1, min(13, len(candidate_row))):
                            scrambled_name = candidate_row[col_num]
                            if scrambled_name and str(scrambled_name).strip():
                                corrected_name = self.fix_candidate_name(str(scrambled_name))
                                if corrected_name and len(corrected_name) > 5:
                                    candidate_names.append(corrected_name)
                                    candidate_vote_totals.append(0)

                        logger.info(f"Extracted {len(candidate_names)} candidate names")

                    # Process data rows (starting from row 2)
                    for row_num, row in enumerate(table[2:], start=2):
                        if not row or len(row) < 2:
                            continue

                        # Check if this is a data row (starts with a number for Serial No.)
                        serial_cell = row[0]
                        if not serial_cell or not str(serial_cell).strip().isdigit():
                            # Skip total rows
                            logger.debug(f"Skipping non-data row: {serial_cell}")
                            continue

                        try:
                            serial_no = int(str(serial_cell).strip())

                            # Extract candidate votes for this polling station
                            candidate_votes_station = []
                            for col_num in range(1, min(13, len(row))):
                                vote_cell = row[col_num]
                                if vote_cell and str(vote_cell).strip().isdigit():
                                    votes = int(str(vote_cell).strip())
                                    candidate_votes_station.append(votes)

                                    # Add to candidate totals
                                    if col_num - 1 < len(candidate_vote_totals):
                                        candidate_vote_totals[col_num - 1] += votes
                                else:
                                    candidate_votes_station.append(0)

                            # Extract summary columns
                            total_valid_votes = 0
                            rejected_votes = 0
                            nota_votes = 0
                            tender_votes = 0

                            # Total valid votes (usually column 13)
                            if len(row) > 13 and row[13] and str(row[13]).strip().isdigit():
                                total_valid_votes = int(str(row[13]).strip())

                            # Rejected votes (usually column 14)
                            if len(row) > 14 and row[14] and str(row[14]).strip().isdigit():
                                rejected_votes = int(str(row[14]).strip())

                            # NOTA calculation
                            candidate_sum = sum(candidate_votes_station)
                            nota_votes = max(0, total_valid_votes - candidate_sum)

                            # Tender votes (if present)
                            if len(row) > 16 and row[16] and str(row[16]).strip().isdigit():
                                tender_votes = int(str(row[16]).strip())

                            polling_data = {
                                'Serial No. Of Polling Station': serial_no,
                                'Total Number of valid votes': total_valid_votes,
                                'Number of Rejected votes': rejected_votes,
                                'NOTA': nota_votes,
                                'Total': total_valid_votes + rejected_votes,
                                'Number Of Tender Votes': tender_votes,
                                'candidate_votes': candidate_votes_station
                            }

                            serial_no_wise_details.append(polling_data)

                        except Exception as e:
                            logger.debug(f"Error processing row: {e}")
                            continue

                        # Enhanced processing completed above

            # Determine elected person (candidate with maximum votes)
            elected_person = None
            max_votes = 0
            if candidate_vote_totals and candidate_names:
                max_votes = max(candidate_vote_totals)
                max_votes_idx = candidate_vote_totals.index(max_votes)
                elected_person = candidate_names[max_votes_idx]

            # Create candidates list
            candidates_list = []
            for i, name in enumerate(candidate_names):
                votes = candidate_vote_totals[i] if i < len(candidate_vote_totals) else 0
                candidates_list.append({
                    'candidate_name': name,
                    'Total Votes Polled': votes
                })

            # Compile final data
            result = {
                'Constituency Number': constituency_info['Constituency Number'],
                'Total Number of Electors': constituency_info['Total Number of Electors'],
                'serial_no_wise_details': serial_no_wise_details,
                'candidates': candidates_list,
                'Elected Person Name': elected_person,
                'candidate_names': candidate_names,
                'candidate_vote_totals': candidate_vote_totals
            }

            return result

    def extract_type2_local_language(self) -> Dict:
        """Extract data from Type 2 (Local Language) PDFs"""
        logger.info("Extracting Type 2 (Local Language) PDF")

        # Similar to Type 1 but with additional handling for Devanagari script
        # For now, using the same logic as Type 1 with unicode support
        return self.extract_type1_standard()

    def extract_type3_scanned(self) -> Optional[Dict]:
        """Extract data from Type 3 (Scanned/Rotated) PDFs using OCR"""
        logger.info("Extracting Type 3 (Scanned/Image) PDF using OCR")

        try:
            # Convert PDF to images
            images = convert_from_path(str(self.pdf_path), dpi=300)

            full_text = ""
            for i, image in enumerate(images):
                logger.info(f"Processing page {i+1} with OCR...")

                # Apply OCR
                text = pytesseract.image_to_string(image, lang='eng+mar')  # English + Marathi
                full_text += text + "\n"

            if not full_text.strip():
                logger.error("OCR failed to extract any text")
                return None

            # Try to extract basic info from OCR text
            constituency_info = self.extract_constituency_info(full_text)

            # For scanned PDFs, we'll return minimal data
            # Full extraction would require more sophisticated OCR processing
            result = {
                'Constituency Number': constituency_info['Constituency Number'],
                'Total Number of Electors': constituency_info['Total Number of Electors'],
                'serial_no_wise_details': [],
                'candidates': [],
                'Elected Person Name': None,
                'note': 'Extracted from scanned PDF using OCR - data may be incomplete'
            }

            return result

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return None

    def process(self) -> bool:
        """Main processing function"""
        try:
            # Find the PDF
            if not self.find_pdf():
                return False

            # Check if already processed
            if self.check_if_already_processed():
                return True

            # Detect PDF type
            self.pdf_type = self.detect_pdf_type()
            logger.info(f"Detected PDF Type: {self.pdf_type}")

            # Extract data based on PDF type
            if self.pdf_type == PDFType.STANDARD:
                self.data = self.extract_type1_standard()
            elif self.pdf_type == PDFType.LOCAL_LANGUAGE:
                self.data = self.extract_type2_local_language()
            elif self.pdf_type == PDFType.SCANNED:
                self.data = self.extract_type3_scanned()
                if not self.data:
                    logger.error(f"Failed to extract data from Type 3 PDF: {self.pdf_path}")
                    return False
            else:
                logger.error(f"Unknown PDF type: {self.pdf_type}")
                return False

            # Save to JSON
            if self.data:
                with open(self.json_output_path, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, indent=2, ensure_ascii=False)
                logger.info(f"Successfully saved data to {self.json_output_path}")
                return True
            else:
                logger.error("No data extracted")
                return False

        except Exception as e:
            logger.error(f"Processing failed: {e}")
            logger.error(traceback.format_exc())
            return False


def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("Usage: python process.py <AC_NUMBER>")
        print("Example: python process.py 222")
        sys.exit(1)

    try:
        ac_number = int(sys.argv[1])
    except ValueError:
        print("Error: AC number must be an integer")
        sys.exit(1)

    logger.info(f"Starting extraction for AC_{ac_number}")

    extractor = Form20Extractor(ac_number)
    success = extractor.process()

    if success:
        logger.info(f"Extraction completed successfully for AC_{ac_number}")
    else:
        logger.error(f"Extraction failed for AC_{ac_number}")
        sys.exit(1)


if __name__ == "__main__":
    main()