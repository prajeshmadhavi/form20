#!/usr/bin/env python3
"""
Improved candidate extraction for AC_15 and similar Type 1 PDFs
"""
import pdfplumber
import json
import re

def fix_candidate_name(scrambled_name):
    """Fix scrambled candidate name from PDF extraction"""
    if not scrambled_name or not scrambled_name.strip():
        return ''

    # Handle the specific scrambling pattern in AC_15
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

def extract_candidate_data_ac15(pdf_path):
    """Extract candidate data specifically from AC_15 type PDFs"""

    result = {
        'constituency_number': 15,
        'total_electors': None,
        'candidate_names': [],
        'candidate_vote_totals': [],
        'polling_station_data': []
    }

    with pdfplumber.open(pdf_path) as pdf:
        # Process first page to get structure
        page = pdf.pages[0]
        tables = page.extract_tables()

        if len(tables) >= 2:
            main_table = tables[1]  # Main data table

            print(f'Processing table with {len(main_table)} rows, {len(main_table[0])} columns')

            # Extract candidate names from Row 1
            if len(main_table) > 1:
                candidate_row = main_table[1]

                # Columns 1-12 contain candidate names
                for col_num in range(1, min(13, len(candidate_row))):
                    scrambled_name = candidate_row[col_num]
                    if scrambled_name and str(scrambled_name).strip():
                        corrected_name = fix_candidate_name(str(scrambled_name))
                        if corrected_name:
                            result['candidate_names'].append(corrected_name)
                            print(f'Candidate {col_num}: {corrected_name}')

            # Extract total electors (should be in table 1)
            if len(tables) >= 1:
                info_table = tables[0]
                if len(info_table) > 0:
                    for row in info_table:
                        for cell in row:
                            if cell and str(cell).isdigit() and len(str(cell)) > 5:
                                result['total_electors'] = int(cell)
                                print(f'Total Electors: {cell}')
                                break
                        if result['total_electors']:
                            break

        # Process all pages for polling station data
        all_polling_data = []
        candidate_vote_totals = [0] * len(result['candidate_names'])

        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()

            if len(tables) >= 2:
                data_table = tables[1]

                # Skip header rows and process data rows
                for row_num, row in enumerate(data_table[2:], start=1):  # Skip rows 0,1
                    if not row or len(row) < 2:
                        continue

                    # Check if first column is a valid serial number
                    serial_cell = row[0]
                    if not serial_cell or not str(serial_cell).strip().isdigit():
                        print(f'Skipping total row: {row[0]} (non-integer)')
                        continue

                    serial_no = int(serial_cell)

                    # Extract vote data for this polling station
                    station_data = {
                        'Serial No. Of Polling Station': serial_no,
                        'candidate_votes': []
                    }

                    # Extract votes for each candidate (columns 1-12)
                    for col_num in range(1, min(13, len(row))):
                        vote_cell = row[col_num]
                        if vote_cell and str(vote_cell).strip().isdigit():
                            votes = int(vote_cell)
                            station_data['candidate_votes'].append(votes)

                            # Add to candidate totals
                            if col_num - 1 < len(candidate_vote_totals):
                                candidate_vote_totals[col_num - 1] += votes
                        else:
                            station_data['candidate_votes'].append(0)

                    # Extract summary columns (total, rejected, NOTA, etc.)
                    if len(row) > 13:
                        total_valid_cell = row[13]
                        if total_valid_cell and str(total_valid_cell).strip().isdigit():
                            station_data['Total Number of valid votes'] = int(total_valid_cell)

                    if len(row) > 14:
                        rejected_cell = row[14]
                        if rejected_cell and str(rejected_cell).strip().isdigit():
                            station_data['Number of Rejected votes'] = int(rejected_cell)

                    # Calculate NOTA and total
                    if 'Total Number of valid votes' in station_data:
                        candidate_sum = sum(station_data['candidate_votes'])
                        station_data['NOTA'] = max(0, station_data['Total Number of valid votes'] - candidate_sum)
                        station_data['Total'] = station_data['Total Number of valid votes'] + station_data.get('Number of Rejected votes', 0)

                    all_polling_data.append(station_data)

        result['polling_station_data'] = all_polling_data
        result['candidate_vote_totals'] = candidate_vote_totals

        print(f'\\nExtracted {len(all_polling_data)} polling stations')
        print(f'Candidate vote totals: {candidate_vote_totals}')

        # Determine elected person (highest votes)
        if candidate_vote_totals and result['candidate_names']:
            max_votes_idx = candidate_vote_totals.index(max(candidate_vote_totals))
            result['elected_person_name'] = result['candidate_names'][max_votes_idx]
            result['elected_person_votes'] = candidate_vote_totals[max_votes_idx]
            print(f'Elected: {result["elected_person_name"]} with {result["elected_person_votes"]} votes')

    return result

# Test the extraction
if __name__ == '__main__':
    pdf_path = 'VIDHANSABHA_2024/Jalgaon/AC_15.pdf'
    result = extract_candidate_data_ac15(pdf_path)

    print('\n=== EXTRACTION RESULTS ===')
    print(f'Constituency: {result["constituency_number"]}')
    print(f'Total Electors: {result["total_electors"]}')
    print(f'Candidates: {len(result["candidate_names"])}')
    print(f'Polling Stations: {len(result["polling_station_data"])}')

    print('\nCandidate Names:')
    for i, name in enumerate(result['candidate_names']):
        votes = result['candidate_vote_totals'][i] if i < len(result['candidate_vote_totals']) else 0
        print(f'  {i+1:2d}. {name} - {votes:,} votes')

    if result['elected_person_name']:
        print(f'\n🏆 Elected: {result["elected_person_name"]} ({result["elected_person_votes"]:,} votes)')