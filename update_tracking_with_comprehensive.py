#!/usr/bin/env python3
"""
Update tracking.json with comprehensive classification results
"""
import json
from datetime import datetime

def update_tracking_with_comprehensive():
    """Update tracking.json with the comprehensive classification results"""

    try:
        # Load both files
        with open('tracking.json', 'r') as f:
            tracking_data = json.load(f)

        with open('comprehensive_classification_results.json', 'r') as f:
            comprehensive_data = json.load(f)

        print("Updating tracking.json with comprehensive classification results...")

        # Create lookup for comprehensive results by AC number
        comprehensive_lookup = {}
        for result in comprehensive_data['classification_results']:
            ac_number = result['ac_number']
            final_type = result.get('final_type', result['recommended_type'])
            comprehensive_lookup[ac_number] = {
                'type': final_type,
                'confidence': result['confidence_score'],
                'manual_override': result.get('manual_override', False),
                'analysis_timestamp': result['analysis_timestamp']
            }

        print(f"Found comprehensive results for {len(comprehensive_lookup)} PDFs")

        # Update tracking data
        updated_count = 0
        for pdf_record in tracking_data['pdfs']:
            ac_number = pdf_record['ac_number']

            if ac_number in comprehensive_lookup:
                comp_result = comprehensive_lookup[ac_number]
                old_type = pdf_record['pdf_type']
                new_type = comp_result['type']

                if old_type != new_type:
                    # Update the PDF record
                    pdf_record['pdf_type'] = new_type
                    pdf_record['pdf_type_description'] = {
                        1: "Type 1 - Standard English Format",
                        2: "Type 2 - Local Language Format",
                        3: "Type 3 - Scanned/Image Format"
                    }[new_type]

                    # Add comprehensive analysis metadata
                    pdf_record['classification_confidence'] = comp_result['confidence']
                    pdf_record['manual_override'] = comp_result['manual_override']
                    pdf_record['comprehensive_analysis_date'] = comp_result['analysis_timestamp']

                    updated_count += 1
                    print(f"  AC_{ac_number}: Type {old_type} → Type {new_type} (confidence: {comp_result['confidence']:.2f})")

                else:
                    # Type didn't change but add metadata
                    pdf_record['classification_confidence'] = comp_result['confidence']
                    pdf_record['manual_override'] = comp_result['manual_override']
                    pdf_record['comprehensive_analysis_date'] = comp_result['analysis_timestamp']

        # Update summary with comprehensive results
        comprehensive_summary = comprehensive_data['summary']
        tracking_data['summary']['type1_count'] = comprehensive_summary['type_distribution'].get('1', 0)
        tracking_data['summary']['type2_count'] = comprehensive_summary['type_distribution'].get('2', 0)
        tracking_data['summary']['type3_count'] = comprehensive_summary['type_distribution'].get('3', 0)
        tracking_data['summary']['last_updated'] = datetime.now().isoformat()
        tracking_data['summary']['comprehensive_analysis_completed'] = True
        tracking_data['summary']['average_classification_confidence'] = comprehensive_summary['average_confidence']

        # Save updated tracking.json
        with open('tracking.json', 'w') as f:
            json.dump(tracking_data, f, indent=2)

        print(f"\n✅ Successfully updated tracking.json!")
        print(f"📊 Updated Classifications:")
        print(f"   Changed: {updated_count} PDFs")
        print(f"   Type 1: {tracking_data['summary']['type1_count']} PDFs")
        print(f"   Type 2: {tracking_data['summary']['type2_count']} PDFs")
        print(f"   Type 3: {tracking_data['summary']['type3_count']} PDFs")
        print(f"   Average Confidence: {tracking_data['summary']['average_classification_confidence']:.3f}")

        # Verification
        total_check = (tracking_data['summary']['type1_count'] +
                      tracking_data['summary']['type2_count'] +
                      tracking_data['summary']['type3_count'])

        print(f"\n🔍 Verification:")
        print(f"   Total types sum: {total_check}")
        print(f"   Expected total: 287")
        print(f"   Match: {'✅' if total_check == 287 else '❌'}")

        return True

    except Exception as e:
        print(f"Error updating tracking.json: {e}")
        return False

if __name__ == "__main__":
    print("Updating tracking.json with Comprehensive Classification Results")
    print("=" * 70)

    success = update_tracking_with_comprehensive()

    if success:
        print("\n🎯 tracking.json is now synchronized with comprehensive analysis!")
        print("📱 Dashboard will show accurate classification data")
    else:
        print("\n❌ Failed to update tracking.json")