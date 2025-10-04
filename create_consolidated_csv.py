#!/usr/bin/env python3
"""
Create consolidated CSV from 53 high-quality Type 1 extractions
"""
import json
import pandas as pd
import os

def create_consolidated_csv():
    """Create consolidated CSV from high-quality extractions"""

    # Load high-quality AC numbers
    with open('high_quality_type1_list.txt', 'r') as f:
        high_quality_acs = list(map(int, f.read().split()))

    print(f"Creating consolidated CSV from {len(high_quality_acs)} high-quality extractions...")

    all_data = []

    for ac_number in high_quality_acs:
        json_file = f"parsedData/AC_{ac_number}.json"

        if not os.path.exists(json_file):
            print(f"Warning: {json_file} not found")
            continue

        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            # Extract constituency-level data
            const_data = {
                'Constituency_Number': data.get('Constituency Number'),
                'Total_Number_of_Electors': data.get('Total Number of Electors'),
                'Elected_Person_Name': data.get('Elected Person Name', ''),
                'Total_Candidates': len(data.get('candidates', [])),
                'Total_Polling_Stations': len(data.get('serial_no_wise_details', []))
            }

            # Add candidate data
            candidates = data.get('candidates', [])
            for i, candidate in enumerate(candidates[:10]):  # Limit to top 10 candidates
                const_data[f'Candidate_{i+1}_Name'] = candidate.get('candidate_name', '')
                const_data[f'Candidate_{i+1}_Votes'] = candidate.get('Total Votes Polled', 0)

            # Calculate total votes
            total_valid_votes = sum(station.get('Total Number of valid votes', 0) for station in data.get('serial_no_wise_details', []))
            total_rejected_votes = sum(station.get('Number of Rejected votes', 0) for station in data.get('serial_no_wise_details', []))
            total_nota_votes = sum(station.get('NOTA', 0) for station in data.get('serial_no_wise_details', []))

            const_data.update({
                'Total_Valid_Votes': total_valid_votes,
                'Total_Rejected_Votes': total_rejected_votes,
                'Total_NOTA_Votes': total_nota_votes,
                'Grand_Total_Votes': total_valid_votes + total_rejected_votes
            })

            all_data.append(const_data)
            print(f"✅ Processed AC_{ac_number}: {const_data['Total_Polling_Stations']} stations, {const_data['Total_Candidates']} candidates")

        except Exception as e:
            print(f"❌ Error processing AC_{ac_number}: {e}")

    # Create DataFrame and save
    if all_data:
        df = pd.DataFrame(all_data)

        # Sort by constituency number
        df = df.sort_values('Constituency_Number')

        # Save to CSV
        output_file = 'HIGH_QUALITY_TYPE1_CONSOLIDATED.csv'
        df.to_csv(output_file, index=False)

        print(f"\\n✅ Consolidated CSV created: {output_file}")
        print(f"📊 Total constituencies: {len(df)}")
        print(f"📋 Total columns: {len(df.columns)}")

        # Show summary statistics
        print(f"\\n📈 Summary Statistics:")
        print(f"   Total electors: {df['Total_Number_of_Electors'].sum():,}")
        print(f"   Total polling stations: {df['Total_Polling_Stations'].sum():,}")
        print(f"   Total candidates: {df['Total_Candidates'].sum():,}")
        print(f"   Total valid votes: {df['Total_Valid_Votes'].sum():,}")

        return output_file
    else:
        print("❌ No data to consolidate")
        return None

if __name__ == "__main__":
    create_consolidated_csv()