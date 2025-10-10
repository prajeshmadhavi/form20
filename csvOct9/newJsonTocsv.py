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
        self.parsed_data_dir = Path(".")  # Current directory (csvOct9)
        self.output_dir = Path("csvData")  # Output in csvOct9/csvData
        self.constituency_mapping_file = Path("../maharashtra_assembly_constituencies.csv")  # Parent directory

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
            "Total EVM Votes",
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

    def get_elected_person_index(self, json_data: Dict) -> int:
        """Find the index of the elected person in candidate_names array"""
        elected_person = json_data.get("Elected Person Name", "")
        candidate_names = json_data.get("candidate_names", [])

        if not elected_person or not candidate_names:
            return -1

        try:
            return candidate_names.index(elected_person)
        except ValueError:
            return -1

    def get_elected_person_votes_from_station(self, station_data: Dict, elected_person_index: int) -> int:
        """Get elected person votes from station candidate_votes array using index"""
        if elected_person_index == -1:
            return 0

        candidate_votes = station_data.get("candidate_votes", [])

        if elected_person_index < len(candidate_votes):
            return candidate_votes[elected_person_index]

        return 0

    def calculate_station_evm_votes(self, station_data: Dict) -> int:
        """Calculate total EVM votes for a station (sum of all candidate_votes)"""
        candidate_votes = station_data.get("candidate_votes", [])
        return sum(candidate_votes)

    def calculate_candidate_totals(self, json_data: Dict) -> List[int]:
        """Calculate total votes for each candidate from polling station data"""
        candidate_names = json_data.get("candidate_names", [])
        num_candidates = len(candidate_names)
        candidate_totals = [0] * num_candidates

        serial_wise_details = json_data.get("serial_no_wise_details", [])

        for station in serial_wise_details:
            votes = station.get("candidate_votes", [])
            for i, vote_count in enumerate(votes):
                if i < num_candidates and vote_count is not None:
                    candidate_totals[i] += vote_count

        return candidate_totals

    def get_elected_person_and_votes(self, json_data: Dict) -> tuple:
        """Find the elected person (candidate with most votes) and their vote count"""
        candidate_names = json_data.get("candidate_names", [])

        if not candidate_names:
            return ("", 0)

        candidate_totals = self.calculate_candidate_totals(json_data)

        if not candidate_totals or max(candidate_totals) == 0:
            return ("", 0)

        max_votes = max(candidate_totals)
        elected_index = candidate_totals.index(max_votes)
        elected_person = candidate_names[elected_index]

        return (elected_person, max_votes)

    def calculate_total_emv_votes(self, json_data: Dict) -> int:
        """Calculate total EMV votes (sum of all candidate votes from all polling stations)"""
        candidate_totals = self.calculate_candidate_totals(json_data)
        return sum(candidate_totals)

    def calculate_total_votes_polled(self, json_data: Dict) -> int:
        """Calculate total votes polled (sum of all valid votes from polling stations)"""
        serial_wise_details = json_data.get("serial_no_wise_details", [])
        total = 0

        for station in serial_wise_details:
            votes = station.get("Total Number of valid votes", 0)
            # Handle None values explicitly
            total += votes if votes is not None else 0

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
            total_electors = ""  # Keep blank as requested
            elected_person = json_data.get("Elected Person Name", "")

            # Get district and constituency names from mapping
            mapping_info = self.constituency_mapping.get(constituency_number, {})
            district_name = mapping_info.get('district_name', '')
            mapped_constituency_name = mapping_info.get('constituency_name', '')

            # Get elected person index for calculations
            elected_person_index = self.get_elected_person_index(json_data)

            # Create CSV data
            csv_rows = []

            # Initialize totals for summary row
            total_summary = {
                'total_valid_votes': 0,
                'total_rejected_votes': 0,
                'total_nota': 0,
                'total_votes': 0,
                'total_tendered_votes': 0,
                'total_elected_person_votes': 0,
                'total_other_candidate_votes': 0,
                'total_evm_votes': 0,
                'total_postal_ballot_votes': 0,
                'total_votes_polled': 0
            }

            # Get polling station details
            serial_wise_details = json_data.get("serial_no_wise_details", [])

            if not serial_wise_details:
                # If no polling station data, create one row with available data
                # Use mapped constituency name if JSON doesn't have one
                final_constituency_name = constituency_name if constituency_name else mapped_constituency_name

                # For files with no polling station data, set all station-specific values to 0
                elected_person_votes = 0
                other_candidate_votes = 0
                total_evm_votes = 0
                postal_ballot_votes = 0
                total_votes_polled = 0

                row = [
                    district_name,                    # District Name
                    "",                               # District No (blank)
                    "",                               # Jilha (blank)
                    final_constituency_name,          # Constituency Name
                    constituency_number,              # Constituency No
                    total_electors,                   # Total No. of Electors (blank)
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
                    total_evm_votes,                  # Total EVM Votes
                    postal_ballot_votes,              # Total Postal ballot votes
                    total_votes_polled                # Total Votes Polled
                ]
                csv_rows.append(row)
            else:
                # Create one row per polling station
                # Use mapped constituency name if JSON doesn't have one
                final_constituency_name = constituency_name if constituency_name else mapped_constituency_name

                for station in serial_wise_details:
                    # Calculate station-specific values
                    station_valid_votes = station.get("Total Number of valid votes", 0)
                    station_rejected_votes = station.get("Number of Rejected votes", 0)
                    station_nota = station.get("NOTA", 0)
                    station_total = station.get("Total", 0)
                    station_tendered_votes = station.get("Number Of Tender Votes", 0)

                    # Calculate EVM votes for this station (sum of candidate_votes)
                    station_evm_votes = self.calculate_station_evm_votes(station)

                    # Calculate elected person votes for this station
                    station_elected_person_votes = self.get_elected_person_votes_from_station(station, elected_person_index)

                    # Calculate other candidate votes for this station
                    station_other_candidate_votes = station_evm_votes - station_elected_person_votes

                    # Total Postal ballot votes = No. of Tendered Votes
                    station_postal_ballot_votes = station_tendered_votes

                    # Total Votes Polled = Total Postal ballot votes + Total EVM Votes
                    station_total_votes_polled = station_postal_ballot_votes + station_evm_votes

                    # Update summary totals
                    total_summary['total_valid_votes'] += station_valid_votes
                    total_summary['total_rejected_votes'] += station_rejected_votes
                    total_summary['total_nota'] += station_nota
                    total_summary['total_votes'] += station_total
                    total_summary['total_tendered_votes'] += station_tendered_votes
                    total_summary['total_elected_person_votes'] += station_elected_person_votes
                    total_summary['total_other_candidate_votes'] += station_other_candidate_votes
                    total_summary['total_evm_votes'] += station_evm_votes
                    total_summary['total_postal_ballot_votes'] += station_postal_ballot_votes
                    total_summary['total_votes_polled'] += station_total_votes_polled

                    row = [
                        district_name,                                          # District Name
                        "",                                                     # District No (blank)
                        "",                                                     # Jilha (blank)
                        final_constituency_name,                               # Constituency Name
                        constituency_number,                                    # Constituency No
                        total_electors,                                         # Total No. of Electors (blank)
                        station.get("Serial No. Of Polling Station", ""),      # Serial Poll
                        station_valid_votes,                                    # Total No. Valid Votes
                        station_rejected_votes,                                 # No. of Rejected Votes
                        station_nota,                                           # NOTA
                        station_total,                                          # Total
                        station_tendered_votes,                                 # No. of Tendered Votes
                        elected_person,                                         # Elected Person Name
                        "",                                                     # Party Name of Elected Person (blank)
                        station_elected_person_votes,                           # No. of Valid Votes Cast in Favour of Elected Person
                        station_other_candidate_votes,                          # Other Candidate Votes
                        station_evm_votes,                                      # Total EVM Votes
                        station_postal_ballot_votes,                            # Total Postal ballot votes
                        station_total_votes_polled                              # Total Votes Polled
                    ]
                    csv_rows.append(row)

            # Add summary row with totals (only if there were polling stations)
            if serial_wise_details:
                summary_row = [
                    "TOTAL",                                    # District Name
                    "",                                         # District No (blank)
                    "",                                         # Jilha (blank)
                    "",                                         # Constituency Name
                    "",                                         # Constituency No
                    "",                                         # Total No. of Electors (blank)
                    "",                                         # Serial Poll (blank)
                    total_summary['total_valid_votes'],         # Total No. Valid Votes
                    total_summary['total_rejected_votes'],      # No. of Rejected Votes
                    total_summary['total_nota'],                # NOTA
                    total_summary['total_votes'],               # Total
                    total_summary['total_tendered_votes'],      # No. of Tendered Votes
                    "",                                         # Elected Person Name
                    "",                                         # Party Name of Elected Person (blank)
                    total_summary['total_elected_person_votes'], # No. of Valid Votes Cast in Favour of Elected Person
                    total_summary['total_other_candidate_votes'], # Other Candidate Votes
                    total_summary['total_evm_votes'],           # Total EVM Votes
                    total_summary['total_postal_ballot_votes'], # Total Postal ballot votes
                    total_summary['total_votes_polled']         # Total Votes Polled
                ]
                csv_rows.append(summary_row)

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
            ["Gondia", "", "", "AMGAON", "15", "", "1", "771", "0", "0", "771", "774", "Anil Patil Bhaidas", "", "366", "405", "771", "774", "1545"],
            ["Gondia", "", "", "AMGAON", "15", "", "2", "690", "0", "0", "690", "691", "Anil Patil Bhaidas", "", "281", "409", "690", "691", "1381"]
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