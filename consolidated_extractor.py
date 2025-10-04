#!/usr/bin/env python3
"""
Consolidated Form 20 PDF Data Extractor
Extracts available fields from Maharashtra VIDHANSABHA_2024 Form 20 PDFs
"""

import os
import re
import csv
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pdfplumber
import fitz
import pandas as pd
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Form20Extractor:
    """Main extractor class for Form 20 PDFs"""

    def __init__(self, base_dir: str = "VIDHANSABHA_2024"):
        self.base_dir = Path(base_dir)
        self.output_dir = Path("extracted_data")
        self.output_dir.mkdir(exist_ok=True)

        # Initialize progress tracking
        self.progress_file = "extraction_progress.json"
        self.load_progress()

        # Extractable fields based on analysis
        self.extractable_fields = [
            'constituency_number', 'constituency_name', 'total_electors',
            'total_valid_votes', 'rejected_votes', 'nota_votes',
            'total_votes', 'tender_votes', 'elected_person_name',
            'elected_person_votes', 'candidate_names', 'candidate_votes'
        ]

    def load_progress(self):
        """Load extraction progress from file"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r') as f:
                    self.progress = json.load(f)
            else:
                self.progress = {
                    'total_pdfs': 0,
                    'processed_pdfs': 0,
                    'successful_extractions': 0,
                    'failed_extractions': 0,
                    'processed_files': [],
                    'failed_files': [],
                    'start_time': None,
                    'last_update': None
                }
        except Exception as e:
            logger.error(f"Error loading progress: {e}")
            self.progress = {}

    def save_progress(self):
        """Save extraction progress to file"""
        try:
            self.progress['last_update'] = datetime.now().isoformat()
            with open(self.progress_file, 'w') as f:
                json.dump(self.progress, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving progress: {e}")

    def find_all_pdfs(self) -> List[Path]:
        """Find all PDF files in the directory structure"""
        pdf_files = list(self.base_dir.glob("**/*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files")
        return pdf_files

    def extract_text_content(self, pdf_path: Path) -> str:
        """Extract text content from PDF using pdfplumber"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return ""

    def parse_constituency_info(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract constituency number and name from text"""
        # Pattern for constituency: "72 BALLARPUR" or similar
        const_pattern = r'(?:FROM THE|CONSTITUENCY)\s*(\d+)\s+([A-Z\s]+)'
        match = re.search(const_pattern, text)

        if match:
            const_num = match.group(1).strip()
            const_name = match.group(2).strip()
            return const_num, const_name

        # Alternative pattern
        alt_pattern = r'(\d+)\s+([A-Z]{3,})'
        alt_match = re.search(alt_pattern, text)
        if alt_match:
            return alt_match.group(1).strip(), alt_match.group(2).strip()

        return None, None

    def extract_total_electors(self, text: str) -> Optional[int]:
        """Extract total number of electors"""
        patterns = [
            r'Total No\.of Electors.*?(\d+)',
            r'Total Number of Electors.*?(\d+)',
            r'Total Electors.*?(\d+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        return None

    def parse_voting_data(self, text: str) -> Dict:
        """Extract voting data from the tabular structure"""
        lines = text.split('\n')
        voting_data = {
            'candidate_names': [],
            'candidate_votes': [],
            'rejected_votes': 0,
            'nota_votes': 0,
            'tender_votes': 0,
            'total_valid_votes': 0
        }

        # Find header line with candidate names
        header_found = False
        vote_lines = []

        for i, line in enumerate(lines):
            # Look for candidate names in header
            if not header_found and any(word in line.upper() for word in ['VALID', 'VOTES', 'CAST', 'FAVOUR']):
                # Extract candidate names from subsequent lines
                potential_names = []
                for j in range(i+1, min(i+5, len(lines))):
                    if re.match(r'^[A-Z\s]+$', lines[j].strip()) and len(lines[j].strip()) > 3:
                        potential_names.extend(lines[j].strip().split())

                voting_data['candidate_names'] = [name for name in potential_names if len(name) > 2][:10]
                header_found = True

            # Look for numeric vote data lines
            if re.match(r'^\d+\s+\d+', line):
                vote_lines.append(line)

        # Process vote lines to extract totals
        if vote_lines:
            candidate_totals = [0] * min(10, len(voting_data['candidate_names']))
            rejected_total = 0
            nota_total = 0
            tender_total = 0

            for line in vote_lines:
                numbers = re.findall(r'\b\d+\b', line)
                if len(numbers) >= 5:  # Minimum expected columns
                    # Extract vote counts (skipping serial numbers)
                    vote_nums = [int(n) for n in numbers[2:] if n.isdigit()]

                    # Add to candidate totals
                    for i, vote in enumerate(vote_nums[:len(candidate_totals)]):
                        if i < len(candidate_totals):
                            candidate_totals[i] += vote

                    # Look for rejected/NOTA in specific positions
                    if len(vote_nums) > len(candidate_totals):
                        # Typically rejected votes are near the end
                        rejected_total += vote_nums[-3] if len(vote_nums) > 3 else 0
                        nota_total += vote_nums[-2] if len(vote_nums) > 2 else 0
                        tender_total += vote_nums[-1] if len(vote_nums) > 1 else 0

            voting_data['candidate_votes'] = candidate_totals
            voting_data['rejected_votes'] = rejected_total
            voting_data['nota_votes'] = nota_total
            voting_data['tender_votes'] = tender_total
            voting_data['total_valid_votes'] = sum(candidate_totals) + nota_total

        return voting_data

    def extract_from_pdf(self, pdf_path: Path) -> Dict:
        """Extract all available data from a single PDF"""
        logger.info(f"Processing: {pdf_path}")

        try:
            # Extract text content
            text = self.extract_text_content(pdf_path)

            if not text:
                logger.warning(f"No text extracted from {pdf_path}")
                return {'error': 'No text content'}

            # Extract constituency info
            const_num, const_name = self.parse_constituency_info(text)

            # Extract total electors
            total_electors = self.extract_total_electors(text)

            # Extract voting data
            voting_data = self.parse_voting_data(text)

            # Determine elected person (highest votes)
            elected_person_name = None
            elected_person_votes = None

            if voting_data['candidate_votes'] and voting_data['candidate_names']:
                max_votes_idx = voting_data['candidate_votes'].index(max(voting_data['candidate_votes']))
                if max_votes_idx < len(voting_data['candidate_names']):
                    elected_person_name = voting_data['candidate_names'][max_votes_idx]
                    elected_person_votes = voting_data['candidate_votes'][max_votes_idx]

            # Compile results
            result = {
                'file_path': str(pdf_path),
                'constituency_number': const_num,
                'constituency_name': const_name,
                'total_electors': total_electors,
                'total_valid_votes': voting_data['total_valid_votes'],
                'rejected_votes': voting_data['rejected_votes'],
                'nota_votes': voting_data['nota_votes'],
                'total_votes': voting_data['total_valid_votes'] + voting_data['rejected_votes'],
                'tender_votes': voting_data['tender_votes'],
                'elected_person_name': elected_person_name,
                'elected_person_votes': elected_person_votes,
                'candidate_names': voting_data['candidate_names'][:10],  # Limit to 10
                'candidate_votes': voting_data['candidate_votes'][:10],   # Limit to 10
                'extraction_timestamp': datetime.now().isoformat(),
                'extraction_quality': self.calculate_quality_score(result)
            }

            return result

        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {e}")
            return {'error': str(e), 'file_path': str(pdf_path)}

    def calculate_quality_score(self, result: Dict) -> float:
        """Calculate quality score based on extracted data completeness"""
        score = 0.0
        total_fields = 8  # Key extractable fields

        if result.get('constituency_number'):
            score += 1
        if result.get('constituency_name'):
            score += 1
        if result.get('total_electors'):
            score += 1
        if result.get('total_valid_votes', 0) > 0:
            score += 1
        if result.get('elected_person_name'):
            score += 1
        if result.get('elected_person_votes', 0) > 0:
            score += 1
        if result.get('candidate_names') and len(result['candidate_names']) > 0:
            score += 1
        if result.get('candidate_votes') and sum(result['candidate_votes']) > 0:
            score += 1

        return score / total_fields

    def save_results_to_csv(self, results: List[Dict], output_file: str = "form20_extracted_data.csv"):
        """Save extraction results to CSV"""
        if not results:
            logger.warning("No results to save")
            return

        # Prepare CSV rows
        csv_rows = []

        for result in results:
            if 'error' in result:
                continue

            row = {
                'file_path': result.get('file_path', ''),
                'constituency_number': result.get('constituency_number', ''),
                'constituency_name': result.get('constituency_name', ''),
                'total_electors': result.get('total_electors', ''),
                'total_valid_votes': result.get('total_valid_votes', ''),
                'rejected_votes': result.get('rejected_votes', ''),
                'nota_votes': result.get('nota_votes', ''),
                'total_votes': result.get('total_votes', ''),
                'tender_votes': result.get('tender_votes', ''),
                'elected_person_name': result.get('elected_person_name', ''),
                'elected_person_votes': result.get('elected_person_votes', ''),
                'extraction_quality': result.get('extraction_quality', 0.0)
            }

            # Add candidate data (up to 10 candidates)
            candidate_names = result.get('candidate_names', [])
            candidate_votes = result.get('candidate_votes', [])

            for i in range(10):
                row[f'candidate_{i+1}_name'] = candidate_names[i] if i < len(candidate_names) else ''
                row[f'candidate_{i+1}_votes'] = candidate_votes[i] if i < len(candidate_votes) else ''

            csv_rows.append(row)

        # Write to CSV
        output_path = self.output_dir / output_file
        df = pd.DataFrame(csv_rows)
        df.to_csv(output_path, index=False)
        logger.info(f"Results saved to {output_path}")

        return output_path

    def process_all_pdfs(self):
        """Process all PDFs and extract data"""
        logger.info("Starting Form 20 PDF extraction process")

        # Find all PDFs
        pdf_files = self.find_all_pdfs()

        if not pdf_files:
            logger.error("No PDF files found")
            return

        # Initialize progress
        self.progress['total_pdfs'] = len(pdf_files)
        self.progress['start_time'] = datetime.now().isoformat()
        self.save_progress()

        results = []

        for i, pdf_path in enumerate(pdf_files):
            # Skip if already processed
            if str(pdf_path) in self.progress.get('processed_files', []):
                logger.info(f"Skipping already processed file: {pdf_path}")
                continue

            logger.info(f"Processing {i+1}/{len(pdf_files)}: {pdf_path.name}")

            # Extract data
            result = self.extract_from_pdf(pdf_path)
            results.append(result)

            # Update progress
            self.progress['processed_pdfs'] += 1

            if 'error' in result:
                self.progress['failed_extractions'] += 1
                self.progress.setdefault('failed_files', []).append(str(pdf_path))
                logger.error(f"Failed to extract from {pdf_path}: {result['error']}")
            else:
                self.progress['successful_extractions'] += 1
                self.progress.setdefault('processed_files', []).append(str(pdf_path))
                logger.info(f"Successfully extracted from {pdf_path} (Quality: {result.get('extraction_quality', 0):.2f})")

            # Save progress every 10 files
            if (i + 1) % 10 == 0:
                self.save_progress()
                logger.info(f"Progress: {self.progress['processed_pdfs']}/{self.progress['total_pdfs']} files processed")

        # Save final results
        csv_file = self.save_results_to_csv(results)
        self.save_progress()

        # Print summary
        logger.info("=" * 50)
        logger.info("EXTRACTION COMPLETE")
        logger.info(f"Total PDFs: {self.progress['total_pdfs']}")
        logger.info(f"Successful: {self.progress['successful_extractions']}")
        logger.info(f"Failed: {self.progress['failed_extractions']}")
        logger.info(f"Results saved to: {csv_file}")
        logger.info("=" * 50)

        return results

def main():
    """Main execution function"""
    print("Form 20 PDF Data Extraction System")
    print("=" * 50)

    # Initialize extractor
    extractor = Form20Extractor()

    # Process all PDFs
    results = extractor.process_all_pdfs()

    print(f"\nExtraction completed. Check 'extracted_data/form20_extracted_data.csv' for results.")
    print(f"Logs available in 'extraction.log'")

if __name__ == "__main__":
    main()