#!/usr/bin/env python3
"""
JSON to CSV Converter for Form 20 Election Data
Converts all JSON files in parsedData folder to CSV format
Each polling station becomes one row in CSV
"""

import json
import csv
import os
from pathlib import Path
from typing import Dict, List, Optional

class JsonToCsvConverter:
    def __init__(self):
        self.parsed_data_dir = Path("parsedData")
        self.output_dir = Path("csvData")
        self.constituency_mapping_file = Path("maharashtra_assembly_constituencies.csv")

        # Create output directory
        self.output_dir.mkdir(exist_ok=True)

        # Load constituency mapping
        self.constituency_mapping = self.load_constituency_mapping()

        # CSV headers as specified
        self.csv_headers = [
            "District Name",
            "District No",
            "Jilha",
            "Constituency Name",
            "Constituency No",
            "Total No. of Electors",
            "Serial Poll",
            "Total No. Valid Votes",
            "No. of Rejected Votes",
            "NOTA",
            "Total",
            "No. of Tendered Votes",
            "Elected Person Name",
            "Party Name of Elected Person",
            "No. of Valid Votes Cast in Favour of Elected Person",
            "Other Candidate Votes",
            "Total EMV Votes",
            "Total Postal ballot votes",
            "Total Votes Polled"
        ]

    def load_constituency_mapping(self) -> Dict[int, Dict[str, str]]:
        """Load constituency number to district name and constituency name mapping"""
        mapping = {}

        if not self.constituency_mapping_file.exists():
            print(f"⚠️ Warning: {self.constituency_mapping_file} not found. District names will be blank.")
            return mapping

        try:
            with open(self.constituency_mapping_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    constituency_num = int(row['Assembly Constituency Number'])
                    district_name = row['District Name']
                    constituency_name = row['Assembly Constituency Name']
                    mapping[constituency_num] = {
                        'district_name': district_name,
                        'constituency_name': constituency_name
                    }

            print(f"✅ Loaded constituency mapping for {len(mapping)} constituencies")
            return mapping

        except Exception as e:
            print(f"⚠️ Error loading constituency mapping: {e}")
            return mapping

    def get_elected_person_votes(self, json_data: Dict) -> int:
        """Find the total votes for the elected person"""
        elected_person = json_data.get("Elected Person Name", "")

        if not elected_person:
            return 0

        candidates = json_data.get("candidates", [])

        # Find the elected person in candidates list
        for candidate in candidates:
            candidate_name = candidate.get("candidate_name", "")
            if candidate_name == elected_person:
                return candidate.get("Total Votes Polled", 0)

        return 0

    def calculate_total_emv_votes(self, json_data: Dict) -> int:
        """Calculate total EMV votes (sum of all candidate votes)"""
        candidates = json_data.get("candidates", [])
        total = 0

        for candidate in candidates:
            total += candidate.get("Total Votes Polled", 0)

        return total

    def calculate_total_votes_polled(self, json_data: Dict) -> int:
        """Calculate total votes polled (sum of all valid votes from polling stations)"""
        serial_wise_details = json_data.get("serial_no_wise_details", [])
        total = 0

        for station in serial_wise_details:
            total += station.get("Total Number of valid votes", 0)

        return total

    def convert_json_to_csv(self, json_file_path: Path) -> bool:
        """Convert a single JSON file to CSV format"""
        try:
            # Load JSON data
            with open(json_file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            # Extract constituency-level data
            constituency_number = json_data.get("Constituency Number", "")
            constituency_name = json_data.get("constituency_name", "")
            total_electors = json_data.get("Total Number of Electors", "")
            elected_person = json_data.get("Elected Person Name", "")

            # Get district and constituency names from mapping
            mapping_info = self.constituency_mapping.get(constituency_number, {})
            district_name = mapping_info.get('district_name', '')
            mapped_constituency_name = mapping_info.get('constituency_name', '')

            # Calculate aggregated values
            elected_person_votes = self.get_elected_person_votes(json_data)
            total_emv_votes = self.calculate_total_emv_votes(json_data)
            other_candidate_votes = total_emv_votes - elected_person_votes
            total_votes_polled = self.calculate_total_votes_polled(json_data)

            # Create CSV data
            csv_rows = []

            # Get polling station details
            serial_wise_details = json_data.get("serial_no_wise_details", [])

            if not serial_wise_details:
                # If no polling station data, create one row with available data
                # Use mapped constituency name if JSON doesn't have one
                final_constituency_name = constituency_name if constituency_name else mapped_constituency_name

                row = [
                    district_name,                    # District Name
                    "",                               # District No (blank)
                    "",                               # Jilha (blank)
                    final_constituency_name,          # Constituency Name
                    constituency_number,              # Constituency No
                    total_electors,                   # Total No. of Electors
                    "",                               # Serial Poll (blank)
                    "",                               # Total No. Valid Votes (blank)
                    "",                               # No. of Rejected Votes (blank)
                    "",                               # NOTA (blank)
                    "",                               # Total (blank)
                    "",                               # No. of Tendered Votes (blank)
                    elected_person,                   # Elected Person Name
                    "",                               # Party Name of Elected Person (blank)
                    elected_person_votes,             # No. of Valid Votes Cast in Favour of Elected Person
                    other_candidate_votes,            # Other Candidate Votes
                    total_emv_votes,                  # Total EMV Votes
                    "",                               # Total Postal ballot votes (blank)
                    total_votes_polled                # Total Votes Polled
                ]
                csv_rows.append(row)
            else:
                # Create one row per polling station
                # Use mapped constituency name if JSON doesn't have one
                final_constituency_name = constituency_name if constituency_name else mapped_constituency_name

                for station in serial_wise_details:
                    row = [
                        district_name,                                          # District Name
                        "",                                                     # District No (blank)
                        "",                                                     # Jilha (blank)
                        final_constituency_name,                               # Constituency Name
                        constituency_number,                                    # Constituency No
                        total_electors,                                         # Total No. of Electors
                        station.get("Serial No. Of Polling Station", ""),      # Serial Poll
                        station.get("Total Number of valid votes", ""),        # Total No. Valid Votes
                        station.get("Number of Rejected votes", ""),           # No. of Rejected Votes
                        station.get("NOTA", ""),                               # NOTA
                        station.get("Total", ""),                              # Total
                        station.get("Number Of Tender Votes", ""),             # No. of Tendered Votes
                        elected_person,                                         # Elected Person Name
                        "",                                                     # Party Name of Elected Person (blank)
                        elected_person_votes,                                   # No. of Valid Votes Cast in Favour of Elected Person
                        other_candidate_votes,                                  # Other Candidate Votes
                        total_emv_votes,                                        # Total EMV Votes
                        "",                                                     # Total Postal ballot votes (blank)
                        total_votes_polled                                      # Total Votes Polled
                    ]
                    csv_rows.append(row)

            # Write CSV file
            csv_file_path = self.output_dir / f"{json_file_path.stem}.csv"

            with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(self.csv_headers)
                writer.writerows(csv_rows)

            print(f"✅ Converted {json_file_path.name} → {csv_file_path.name} ({len(csv_rows)} rows)")
            return True

        except Exception as e:
            print(f"❌ Error converting {json_file_path.name}: {e}")
            return False

    def convert_all_json_files(self):
        """Convert all JSON files in the parsedData directory"""
        if not self.parsed_data_dir.exists():
            print(f"❌ Directory {self.parsed_data_dir} not found!")
            return

        # Find all JSON files
        json_files = list(self.parsed_data_dir.glob("AC_*.json"))

        if not json_files:
            print(f"❌ No AC_*.json files found in {self.parsed_data_dir}")
            return

        print(f"🚀 Starting conversion of {len(json_files)} JSON files")
        print(f"📁 Output directory: {self.output_dir}")
        print("=" * 60)

        successful = 0
        failed = 0

        for json_file in sorted(json_files):
            if self.convert_json_to_csv(json_file):
                successful += 1
            else:
                failed += 1

        print("=" * 60)
        print(f"🎉 Conversion completed!")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Total: {len(json_files)}")

        if failed > 0:
            print(f"⚠️ Check error messages above for failed conversions")

    def create_sample_csv(self):
        """Create a sample CSV to show the expected format"""
        sample_data = [
            ["Gondia", "", "", "AMGAON", "15", "308272", "1", "771", "0", "0", "771", "774", "Anil Patil Bhaidas", "", "107236", "14573", "121809", "", "121809"],
            ["Gondia", "", "", "AMGAON", "15", "308272", "2", "690", "0", "0", "690", "691", "Anil Patil Bhaidas", "", "107236", "14573", "121809", "", "121809"]
        ]

        sample_file = self.output_dir / "sample_format.csv"
        with open(sample_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(self.csv_headers)
            writer.writerows(sample_data)

        print(f"📋 Sample CSV format created: {sample_file}")

def main():
    converter = JsonToCsvConverter()

    print("📊 JSON to CSV Converter for Form 20 Election Data")
    print("=" * 60)

    # Create sample format file
    converter.create_sample_csv()

    # Convert all JSON files
    converter.convert_all_json_files()

def test_single_file(ac_number):
    """Test conversion of a single file"""
    converter = JsonToCsvConverter()
    json_file = converter.parsed_data_dir / f"AC_{ac_number}.json"

    if json_file.exists():
        print(f"Testing conversion of {json_file.name}")
        converter.convert_json_to_csv(json_file)
    else:
        print(f"File AC_{ac_number}.json not found")

if __name__ == "__main__":
    main()