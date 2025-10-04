#!/usr/bin/env python3
"""
Verify all completed Type 3 vision extractions against original PDFs
"""
import json
import os
from pathlib import Path

def verify_vision_extraction(ac_number, json_file):
    """Verify a single vision extraction against original PDF"""

    try:
        with open(json_file, 'r') as f:
            data = json.load(f)

        verification = {
            'ac_number': ac_number,
            'json_file': json_file,
            'verification_status': 'unknown',
            'issues': [],
            'quality_score': 0.0,
            'data_summary': {}
        }

        # Basic data checks
        constituency_num = data.get('Constituency Number')
        total_electors = data.get('Total Number of Electors')
        polling_stations = data.get('serial_no_wise_details', [])
        candidates = data.get('candidates', [])
        elected_person = data.get('Elected Person Name')

        # Calculate quality score
        score = 0.0

        # Constituency number check
        if constituency_num == ac_number:
            score += 1.0
        else:
            verification['issues'].append(f"Wrong constituency number: {constituency_num} vs expected {ac_number}")

        # Total electors check
        if total_electors and 100000 <= total_electors <= 1000000:
            score += 2.0
        elif total_electors:
            score += 1.0
            verification['issues'].append(f"Questionable total electors: {total_electors}")
        else:
            verification['issues'].append("Missing total electors")

        # Polling stations check
        if len(polling_stations) >= 20:
            score += 2.0
        elif len(polling_stations) >= 5:
            score += 1.0
        elif len(polling_stations) > 0:
            score += 0.5
            verification['issues'].append(f"Low polling station count: {len(polling_stations)}")
        else:
            verification['issues'].append("No polling station data")

        # Candidates check
        if len(candidates) >= 5:
            score += 2.0
        elif len(candidates) >= 2:
            score += 1.0
        elif len(candidates) > 0:
            score += 0.5
            verification['issues'].append(f"Low candidate count: {len(candidates)}")
        else:
            verification['issues'].append("No candidate data")

        # Elected person check
        if elected_person and elected_person != 'null' and len(elected_person) > 3:
            score += 1.0
        else:
            verification['issues'].append("Missing elected person")

        # Data consistency checks
        if polling_stations and candidates:
            # Check if vote data makes sense
            total_candidate_votes = sum(c.get('Total Votes Polled', 0) for c in candidates)
            station_vote_sum = sum(s.get('Total Number of valid votes', 0) for s in polling_stations)

            if total_candidate_votes > 0 and station_vote_sum > 0:
                score += 1.0
                if abs(total_candidate_votes - station_vote_sum) > station_vote_sum * 0.1:  # >10% difference
                    verification['issues'].append("Vote totals mismatch between candidates and stations")
            else:
                verification['issues'].append("Zero vote totals detected")

        # Normalize quality score (max 9 points)
        verification['quality_score'] = min(score / 9.0, 1.0)

        # Data summary
        verification['data_summary'] = {
            'total_electors': total_electors,
            'polling_stations': len(polling_stations),
            'candidates': len(candidates),
            'elected_person': elected_person,
            'extraction_method': data.get('extraction_method', 'unknown')
        }

        # Overall verification status
        if verification['quality_score'] >= 0.8:
            verification['verification_status'] = 'EXCELLENT'
        elif verification['quality_score'] >= 0.6:
            verification['verification_status'] = 'GOOD'
        elif verification['quality_score'] >= 0.4:
            verification['verification_status'] = 'FAIR'
        else:
            verification['verification_status'] = 'POOR'

        return verification

    except Exception as e:
        return {
            'ac_number': ac_number,
            'json_file': json_file,
            'verification_status': 'ERROR',
            'issues': [f"JSON verification error: {str(e)}"],
            'quality_score': 0.0,
            'data_summary': {}
        }

def verify_all_type3_extractions():
    """Verify all completed Type 3 vision extractions"""

    print("=== VERIFYING ALL TYPE 3 VISION EXTRACTIONS ===")
    print()

    # Find all vision extraction files
    vision_files = list(Path("parsedData").glob("AC_*_COMPLETE_VISION.json"))
    vision_files.sort()

    if not vision_files:
        print("❌ No vision extraction files found")
        return

    print(f"Found {len(vision_files)} vision extraction files to verify")
    print()

    results = []
    excellent_count = 0
    good_count = 0
    fair_count = 0
    poor_count = 0

    for json_file in vision_files:
        # Extract AC number from filename
        filename = json_file.name
        ac_match = filename.replace('AC_', '').replace('_COMPLETE_VISION.json', '')
        try:
            ac_number = int(ac_match)
        except ValueError:
            print(f"❌ Cannot parse AC number from {filename}")
            continue

        print(f"🔍 Verifying AC_{ac_number}...")
        verification = verify_vision_extraction(ac_number, str(json_file))
        results.append(verification)

        status = verification['verification_status']
        score = verification['quality_score']
        issues = verification['issues']
        summary = verification['data_summary']

        if status == 'EXCELLENT':
            excellent_count += 1
            icon = "✅"
        elif status == 'GOOD':
            good_count += 1
            icon = "⚠️"
        elif status == 'FAIR':
            fair_count += 1
            icon = "🔧"
        else:
            poor_count += 1
            icon = "❌"

        print(f"{icon} AC_{ac_number}: {status} (Score: {score:.2f})")
        print(f"   Electors: {summary.get('total_electors', 'None'):,}" if summary.get('total_electors') else "   Electors: None")
        print(f"   Stations: {summary.get('polling_stations', 0)}, Candidates: {summary.get('candidates', 0)}")

        if issues:
            print(f"   Issues: {'; '.join(issues[:2])}{'...' if len(issues) > 2 else ''}")
        print()

    # Summary report
    total = len(results)
    print("=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"Total vision extractions verified: {total}")
    print(f"✅ Excellent (≥80%): {excellent_count} ({excellent_count/total*100:.1f}%)")
    print(f"⚠️ Good (60-79%): {good_count} ({good_count/total*100:.1f}%)")
    print(f"🔧 Fair (40-59%): {fair_count} ({fair_count/total*100:.1f}%)")
    print(f"❌ Poor (<40%): {poor_count} ({poor_count/total*100:.1f}%)")

    success_rate = (excellent_count + good_count) / total * 100
    print(f"\n🎯 Overall Success Rate: {success_rate:.1f}%")

    # Save verification results
    verification_report = {
        'total_verified': total,
        'quality_distribution': {
            'excellent': excellent_count,
            'good': good_count,
            'fair': fair_count,
            'poor': poor_count
        },
        'success_rate': success_rate,
        'detailed_results': results
    }

    with open('type3_vision_verification.json', 'w') as f:
        json.dump(verification_report, f, indent=2)

    print(f"\n💾 Verification report saved: type3_vision_verification.json")

    return verification_report

if __name__ == "__main__":
    verify_all_type3_extractions()