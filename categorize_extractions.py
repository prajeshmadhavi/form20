#!/usr/bin/env python3
"""
Categorize Type 1 extractions by quality and create focused reports
"""
import json
import os
from quality_checker import analyze_json_quality

def categorize_type1_extractions():
    """Categorize Type 1 extractions by quality"""

    # Get list of expected Type 1 ACs
    with open('tracking.json', 'r') as f:
        tracking_data = json.load(f)

    type1_acs = [p['ac_number'] for p in tracking_data['pdfs'] if p['pdf_type'] == 1]
    type1_acs.sort()

    print("Analyzing all Type 1 extractions...")

    high_quality = []      # ≥80% quality
    medium_quality = []    # 60-79% quality
    low_quality = []       # <60% quality
    missing_files = []

    for ac_number in type1_acs:
        json_path = f"parsedData/AC_{ac_number}.json"

        if not os.path.exists(json_path):
            missing_files.append(ac_number)
            continue

        quality_result = analyze_json_quality(json_path, ac_number)
        score = quality_result['quality_score']

        entry = {
            'ac_number': ac_number,
            'quality_score': score,
            'issues': quality_result['issues'],
            'total_electors': quality_result['total_electors'],
            'polling_stations': quality_result['polling_stations'],
            'candidates': quality_result['candidates'],
            'elected_person': quality_result['elected_person']
        }

        if score >= 0.8:
            high_quality.append(entry)
        elif score >= 0.6:
            medium_quality.append(entry)
        else:
            low_quality.append(entry)

    # Create categorized reports
    categories = {
        'high_quality': {
            'title': 'High Quality Type 1 Extractions (≥80%)',
            'data': high_quality,
            'description': 'Ready for immediate use - comprehensive data extracted'
        },
        'medium_quality': {
            'title': 'Medium Quality Type 1 Extractions (60-79%)',
            'data': medium_quality,
            'description': 'Usable with minor issues - may need review'
        },
        'low_quality': {
            'title': 'Low Quality Type 1 Extractions (<60%)',
            'data': low_quality,
            'description': 'Need reprocessing or reclassification'
        }
    }

    # Print detailed breakdown
    print("\n" + "="*70)
    print("📊 TYPE 1 EXTRACTION CATEGORIZATION")
    print("="*70)

    for category_key, category in categories.items():
        print(f"\n{category['title']}")
        print(f"Count: {len(category['data'])} PDFs")
        print(f"Description: {category['description']}")
        print()

        if category['data']:
            print("AC Numbers:")
            ac_list = [str(entry['ac_number']) for entry in category['data']]
            # Print in rows of 10
            for i in range(0, len(ac_list), 10):
                row = ac_list[i:i+10]
                print(f"  {' '.join(row)}")

            print("\nTop examples:")
            for entry in category['data'][:5]:
                ac = entry['ac_number']
                score = entry['quality_score']
                stations = entry['polling_stations']
                candidates = entry['candidates']
                print(f"  AC_{ac}: Score {score:.2f} - {stations} stations, {candidates} candidates")

    # Create summary files
    summary_data = {
        'analysis_date': '2024-09-28',
        'total_type1_pdfs': len(type1_acs),
        'categorization': {
            'high_quality': {
                'count': len(high_quality),
                'ac_numbers': [e['ac_number'] for e in high_quality],
                'average_score': sum(e['quality_score'] for e in high_quality) / len(high_quality) if high_quality else 0
            },
            'medium_quality': {
                'count': len(medium_quality),
                'ac_numbers': [e['ac_number'] for e in medium_quality],
                'average_score': sum(e['quality_score'] for e in medium_quality) / len(medium_quality) if medium_quality else 0
            },
            'low_quality': {
                'count': len(low_quality),
                'ac_numbers': [e['ac_number'] for e in low_quality],
                'average_score': sum(e['quality_score'] for e in low_quality) / len(low_quality) if low_quality else 0
            }
        },
        'success_metrics': {
            'overall_success_rate': (len(high_quality) + len(medium_quality)) / len(type1_acs) * 100,
            'high_quality_rate': len(high_quality) / len(type1_acs) * 100,
            'immediate_usability_rate': len(high_quality) / len(type1_acs) * 100
        }
    }

    # Save categorization results
    with open('type1_extraction_analysis.json', 'w') as f:
        json.dump(summary_data, f, indent=2)

    print(f"\n💾 Analysis saved to: type1_extraction_analysis.json")

    # Focus recommendations
    print("\n" + "="*70)
    print("🎯 FOCUS RECOMMENDATIONS")
    print("="*70)
    print(f"✅ IMMEDIATE USE: {len(high_quality)} high-quality PDFs ready")
    print(f"⚠️ REVIEW NEEDED: {len(medium_quality)} medium-quality PDFs")
    print(f"🔧 NEEDS WORK: {len(low_quality)} low-quality PDFs require attention")
    print()
    print(f"📈 Success Rate: {summary_data['success_metrics']['overall_success_rate']:.1f}%")
    print(f"📊 Immediate Usability: {summary_data['success_metrics']['immediate_usability_rate']:.1f}%")

    return summary_data

if __name__ == "__main__":
    categorize_type1_extractions()