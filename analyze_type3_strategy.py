#!/usr/bin/env python3
"""
Analyze Type 3 PDFs and create strategic processing approach
"""
import json
import os
from pathlib import Path
import fitz
import pdfplumber

def analyze_type3_pdf_complexity(ac_number):
    """Analyze complexity of a Type 3 PDF"""

    # Find PDF file
    base_dir = Path("VIDHANSABHA_2024")
    pdf_path = None

    for district_dir in base_dir.iterdir():
        if district_dir.is_dir():
            for pdf_file in district_dir.glob(f"AC_{ac_number:02d}.pdf"):
                pdf_path = pdf_file
                break
        if pdf_path:
            break

    if not pdf_path or not pdf_path.exists():
        return None

    analysis = {
        'ac_number': ac_number,
        'file_path': str(pdf_path),
        'file_size_mb': round(pdf_path.stat().st_size / 1024 / 1024, 2),
        'page_count': 0,
        'total_images': 0,
        'images_per_page': 0,
        'text_extractable': False,
        'text_length': 0,
        'complexity_tier': 1,
        'estimated_processing_time': 0,
        'ocr_confidence_estimate': 'unknown'
    }

    try:
        # Analyze with PyMuPDF for images and basic info
        doc = fitz.open(pdf_path)
        analysis['page_count'] = len(doc)

        total_images = 0
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()
            total_images += len(image_list)

            # Test text extraction
            text = page.get_text()
            if text and text.strip():
                analysis['text_extractable'] = True
                analysis['text_length'] += len(text.strip())

        analysis['total_images'] = total_images
        analysis['images_per_page'] = total_images / max(analysis['page_count'], 1)

        doc.close()

        # Determine complexity tier
        if analysis['images_per_page'] <= 2 and analysis['file_size_mb'] <= 5:
            analysis['complexity_tier'] = 1  # Simple
            analysis['estimated_processing_time'] = 30  # seconds
            analysis['ocr_confidence_estimate'] = 'high'
        elif analysis['images_per_page'] <= 10 and analysis['file_size_mb'] <= 15:
            analysis['complexity_tier'] = 2  # Medium
            analysis['estimated_processing_time'] = 90
            analysis['ocr_confidence_estimate'] = 'medium'
        else:
            analysis['complexity_tier'] = 3  # Complex
            analysis['estimated_processing_time'] = 180
            analysis['ocr_confidence_estimate'] = 'low'

    except Exception as e:
        analysis['error'] = str(e)

    return analysis

def create_type3_strategy():
    """Create comprehensive Type 3 processing strategy"""

    # Load Type 3 PDFs from tracking
    with open('tracking.json', 'r') as f:
        tracking_data = json.load(f)

    type3_pdfs = [p for p in tracking_data['pdfs'] if p['pdf_type'] == 3]
    type3_pdfs.sort(key=lambda x: x['ac_number'])

    print(f"=== ANALYZING {len(type3_pdfs)} TYPE 3 PDFS FOR STRATEGY ===")

    # Analyze a representative sample
    sample_acs = [p['ac_number'] for p in type3_pdfs[::20]]  # Every 20th PDF
    if len(sample_acs) < 10:
        sample_acs = [p['ac_number'] for p in type3_pdfs[:10]]  # First 10 if small sample

    analyses = []
    tier1_count = 0
    tier2_count = 0
    tier3_count = 0

    print(f"Analyzing sample of {len(sample_acs)} PDFs...")

    for ac_number in sample_acs:
        analysis = analyze_type3_pdf_complexity(ac_number)
        if analysis:
            analyses.append(analysis)

            tier = analysis['complexity_tier']
            if tier == 1:
                tier1_count += 1
            elif tier == 2:
                tier2_count += 1
            else:
                tier3_count += 1

            print(f"AC_{ac_number}: {analysis['file_size_mb']}MB, {analysis['total_images']} images, Tier {tier}")

    # Project to full dataset
    total_type3 = len(type3_pdfs)
    sample_size = len(analyses)

    if sample_size > 0:
        projected_tier1 = int(tier1_count / sample_size * total_type3)
        projected_tier2 = int(tier2_count / sample_size * total_type3)
        projected_tier3 = int(tier3_count / sample_size * total_type3)

        # Calculate processing time estimates
        tier1_time = projected_tier1 * 30  # 30 seconds each
        tier2_time = projected_tier2 * 90  # 90 seconds each
        tier3_time = projected_tier3 * 180  # 180 seconds each
        total_time_seconds = tier1_time + tier2_time + tier3_time

        total_hours = total_time_seconds / 3600

        print("\\n" + "="*60)
        print("📊 TYPE 3 PROCESSING STRATEGY")
        print("="*60)

        print(f"\\n🎯 Complexity Distribution (Projected):")
        print(f"   Tier 1 (Simple): {projected_tier1} PDFs (~{projected_tier1/total_type3*100:.1f}%)")
        print(f"   Tier 2 (Medium): {projected_tier2} PDFs (~{projected_tier2/total_type3*100:.1f}%)")
        print(f"   Tier 3 (Complex): {projected_tier3} PDFs (~{projected_tier3/total_type3*100:.1f}%)")

        print(f"\\n⏱️ Processing Time Estimates:")
        print(f"   Tier 1: {tier1_time/3600:.1f} hours")
        print(f"   Tier 2: {tier2_time/3600:.1f} hours")
        print(f"   Tier 3: {tier3_time/3600:.1f} hours")
        print(f"   Total: {total_hours:.1f} hours ({total_hours/24:.1f} days)")

        print(f"\\n🎯 Recommended Processing Order:")
        print(f"1. Start with Tier 1 (Simple) - {projected_tier1} PDFs")
        print(f"   • Single images, small files")
        print(f"   • High OCR success rate expected")
        print(f"   • Quick wins to build momentum")
        print()
        print(f"2. Progress to Tier 2 (Medium) - {projected_tier2} PDFs")
        print(f"   • Multiple images, medium files")
        print(f"   • Good OCR success rate with preprocessing")
        print(f"   • Standard processing pipeline")
        print()
        print(f"3. Tackle Tier 3 (Complex) - {projected_tier3} PDFs")
        print(f"   • Many images, large files")
        print(f"   • Requires advanced preprocessing")
        print(f"   • Manual review likely needed")

        # Save strategy
        strategy_data = {
            'total_type3_pdfs': total_type3,
            'sample_analyzed': sample_size,
            'complexity_distribution': {
                'tier1_simple': projected_tier1,
                'tier2_medium': projected_tier2,
                'tier3_complex': projected_tier3
            },
            'time_estimates': {
                'tier1_hours': tier1_time / 3600,
                'tier2_hours': tier2_time / 3600,
                'tier3_hours': tier3_time / 3600,
                'total_hours': total_hours
            },
            'processing_order': [
                'tier1_simple_pdfs',
                'tier2_medium_pdfs',
                'tier3_complex_pdfs'
            ],
            'sample_analyses': analyses
        }

        with open('type3_processing_strategy.json', 'w') as f:
            json.dump(strategy_data, f, indent=2)

        print(f"\\n💾 Strategy saved to: type3_processing_strategy.json")

        return strategy_data

    else:
        print("❌ No successful analyses - cannot create strategy")
        return None

def get_tier1_type3_pdfs():
    """Get list of simple Tier 1 Type 3 PDFs to start with"""

    with open('tracking.json', 'r') as f:
        tracking_data = json.load(f)

    type3_pdfs = [p for p in tracking_data['pdfs'] if p['pdf_type'] == 3]

    # Analyze first 20 to find simple ones
    simple_pdfs = []

    for pdf in type3_pdfs[:20]:
        ac_number = pdf['ac_number']
        analysis = analyze_type3_pdf_complexity(ac_number)

        if analysis and analysis['complexity_tier'] == 1:
            simple_pdfs.append(ac_number)

    print(f"\\n🎯 RECOMMENDED STARTING PDFs (Tier 1 - Simple):")
    print(f"AC Numbers: {simple_pdfs}")

    return simple_pdfs

if __name__ == "__main__":
    strategy = create_type3_strategy()
    if strategy:
        simple_pdfs = get_tier1_type3_pdfs()
        print(f"\\n🚀 Ready to start with {len(simple_pdfs)} simple Type 3 PDFs")