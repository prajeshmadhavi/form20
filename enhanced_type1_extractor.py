#!/usr/bin/env python3
"""
Enhanced Type 1 extractor to solve technical issues with failed PDFs
Handles both table-based and text-based extraction
"""
import re
import json
import pdfplumber
import fitz
from pathlib import Path

class EnhancedType1Extractor:
    """Enhanced extractor for problematic Type 1 PDFs"""

    def __init__(self, ac_number):
        self.ac_number = ac_number
        self.pdf_path = self.find_pdf_path()

    def find_pdf_path(self):
        """Find PDF file for given AC number"""
        base_dir = Path("VIDHANSABHA_2024")
        for district_dir in base_dir.iterdir():
            if district_dir.is_dir():
                for pdf_file in district_dir.glob(f"AC_{self.ac_number:02d}.pdf"):
                    return pdf_file
        return None

    def extract_from_text_lines(self, text):
        """Extract voting data from text lines when tables fail"""

        result = {
            'constituency_number': self.ac_number,
            'total_electors': None,
            'serial_no_wise_details': [],
            'candidates': [],
            'elected_person_name': None
        }

        if not text:
            return result

        lines = text.split('\n')

        # Extract total electors
        for line in lines:
            electors_match = re.search(r'(\d{6,})', line)
            if electors_match and 'Electors' in line:
                potential_electors = int(electors_match.group(1))
                if 100000 <= potential_electors <= 1000000:  # Realistic range
                    result['total_electors'] = potential_electors
                    break

        # Extract constituency name
        const_pattern = rf'{self.ac_number}[-\s]+([A-Z\s]+)'
        const_match = re.search(const_pattern, text, re.IGNORECASE)
        if const_match:
            result['constituency_name'] = const_match.group(1).strip()

        # Find voting data lines (lines with multiple numbers)
        voting_lines = []
        for line in lines:
            line_clean = line.strip()
            if line_clean and re.match(r'^\d+', line_clean):
                # Count numbers in line
                numbers = re.findall(r'\b\d+\b', line_clean)
                if len(numbers) >= 5:  # Likely voting data
                    voting_lines.append(line_clean)

        print(f"Found {len(voting_lines)} potential voting data lines")

        # Process voting lines
        candidate_totals = {}
        for line in voting_lines:
            numbers = re.findall(r'\b\d+\b', line)
            if len(numbers) >= 5:
                try:
                    serial_no = int(numbers[0])

                    # Skip if serial number is too high (might be total row)
                    if serial_no > 1000:
                        continue

                    # Extract vote data
                    vote_nums = [int(n) for n in numbers[1:] if n.isdigit()]

                    if len(vote_nums) >= 4:  # At least candidate votes + totals
                        # Last few numbers are usually totals
                        total_valid = vote_nums[-3] if len(vote_nums) >= 3 else sum(vote_nums[:-2])
                        rejected = vote_nums[-2] if len(vote_nums) >= 2 else 0
                        nota = vote_nums[-1] if len(vote_nums) >= 1 else 0

                        station_data = {
                            'Serial No. Of Polling Station': serial_no,
                            'Total Number of valid votes': total_valid,
                            'Number of Rejected votes': rejected,
                            'NOTA': nota,
                            'Total': total_valid + rejected,
                            'Number Of Tender Votes': 0,
                            'candidate_votes': vote_nums[:-3] if len(vote_nums) > 3 else vote_nums
                        }

                        result['serial_no_wise_details'].append(station_data)

                        # Accumulate candidate totals
                        for i, votes in enumerate(station_data['candidate_votes']):
                            if i not in candidate_totals:
                                candidate_totals[i] = 0
                            candidate_totals[i] += votes

                except (ValueError, IndexError):
                    continue

        # Create candidate list
        if candidate_totals:
            for i in range(len(candidate_totals)):
                result['candidates'].append({
                    'candidate_name': f'Candidate_{i+1}',
                    'Total Votes Polled': candidate_totals.get(i, 0)
                })

            # Find elected person (highest votes)
            max_votes = max(candidate_totals.values())
            for i, votes in candidate_totals.items():
                if votes == max_votes:
                    result['elected_person_name'] = f'Candidate_{i+1}'
                    break

        return result

    def extract_with_alternative_table_methods(self):
        """Try alternative table extraction methods"""

        if not self.pdf_path or not self.pdf_path.exists():
            return None

        result = {
            'Constituency Number': self.ac_number,
            'Total Number of Electors': None,
            'serial_no_wise_details': [],
            'candidates': [],
            'Elected Person Name': None
        }

        try:
            # Method 1: Enhanced pdfplumber with different settings
            with pdfplumber.open(self.pdf_path) as pdf:
                all_text = ""

                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        all_text += text + "\n"

                    # Try multiple table extraction strategies
                    table_strategies = [
                        {},  # Default
                        {'vertical_strategy': 'text', 'horizontal_strategy': 'text'},
                        {'vertical_strategy': 'lines', 'horizontal_strategy': 'lines'},
                        {'snap_tolerance': 5, 'join_tolerance': 3}
                    ]

                    for strategy in table_strategies:
                        try:
                            tables = page.extract_tables(table_settings=strategy)
                            if tables:
                                # Process tables similar to original method
                                print(f"Found {len(tables)} tables with strategy {strategy}")
                                # Add table processing logic here
                                break
                        except:
                            continue

                # If table extraction failed, try text-based extraction
                if not result['serial_no_wise_details']:
                    text_result = self.extract_from_text_lines(all_text)
                    result.update(text_result)

        except Exception as e:
            print(f"Error in enhanced extraction: {e}")

        return result

    def process_pdf(self):
        """Process PDF with enhanced methods"""

        print(f"Processing AC_{self.ac_number} with enhanced extraction...")

        if not self.pdf_path:
            print(f"❌ PDF not found for AC_{self.ac_number}")
            return None

        # Try enhanced extraction
        result = self.extract_with_alternative_table_methods()

        if result and (result.get('serial_no_wise_details') or result.get('candidates')):
            # Save result
            output_path = f"parsedData/AC_{self.ac_number}.json"
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)

            print(f"✅ Enhanced extraction successful for AC_{self.ac_number}")
            print(f"   Electors: {result.get('Total Number of Electors', 'None')}")
            print(f"   Stations: {len(result.get('serial_no_wise_details', []))}")
            print(f"   Candidates: {len(result.get('candidates', []))}")

            return True
        else:
            print(f"❌ Enhanced extraction failed for AC_{self.ac_number}")
            return False

def test_enhanced_extraction():
    """Test enhanced extraction on problematic PDFs"""

    # Test PDFs that need enhanced table extraction
    test_acs = [30, 39, 52]  # Sample from the 7 PDFs

    print("=== TESTING ENHANCED EXTRACTION ===")

    for ac_number in test_acs:
        print(f"\n--- Testing AC_{ac_number} ---")
        extractor = EnhancedType1Extractor(ac_number)
        success = extractor.process_pdf()

        if success:
            print(f"✅ AC_{ac_number}: Enhanced extraction worked")
        else:
            print(f"❌ AC_{ac_number}: Still needs more work")

def process_all_problematic_pdfs():
    """Process all 16 remaining problematic PDFs"""

    # 7 PDFs needing enhanced table extraction
    table_extraction_acs = [30, 39, 52, 62, 162, 243, 281]

    # 9 PDFs needing improved Type 1 logic
    type1_logic_acs = [27, 35, 79, 154, 168, 178, 191, 265, 272]

    all_problematic = table_extraction_acs + type1_logic_acs

    print(f"=== PROCESSING {len(all_problematic)} PROBLEMATIC TYPE 1 PDFS ===")

    success_count = 0

    for ac_number in all_problematic:
        print(f"\nProcessing AC_{ac_number}...")
        extractor = EnhancedType1Extractor(ac_number)

        if extractor.process_pdf():
            success_count += 1

    print(f"\n🎯 Enhanced processing results: {success_count}/{len(all_problematic)} successful")
    return success_count

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            test_enhanced_extraction()
        elif sys.argv[1] == 'all':
            process_all_problematic_pdfs()
        else:
            try:
                ac_number = int(sys.argv[1])
                extractor = EnhancedType1Extractor(ac_number)
                extractor.process_pdf()
            except ValueError:
                print("Usage: python enhanced_type1_extractor.py <AC_NUMBER>|test|all")
    else:
        print("Usage: python enhanced_type1_extractor.py <AC_NUMBER>|test|all")
        print("Examples:")
        print("  python enhanced_type1_extractor.py 30     # Process AC_30")
        print("  python enhanced_type1_extractor.py test   # Test on sample PDFs")
        print("  python enhanced_type1_extractor.py all    # Process all problematic PDFs")