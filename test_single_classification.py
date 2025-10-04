#!/usr/bin/env python3
"""
Test the comprehensive classifier on a single PDF
"""
from comprehensive_classifier import PDFAnalyzer
from pathlib import Path
import json

def test_single_pdf(ac_number):
    """Test classification of a single PDF"""

    # Find the PDF file
    pdf_path = None
    base_dir = Path("VIDHANSABHA_2024")

    for district_dir in base_dir.iterdir():
        if district_dir.is_dir():
            for pdf_file in district_dir.glob(f"AC_{ac_number:02d}.pdf"):
                pdf_path = pdf_file
                break
            if pdf_path:
                break

    if not pdf_path or not pdf_path.exists():
        print(f"❌ PDF for AC_{ac_number} not found")
        return

    print(f"🔍 Testing AC_{ac_number}: {pdf_path}")
    print("="*60)

    # Analyze the PDF
    analyzer = PDFAnalyzer(pdf_path)
    analysis = analyzer.analyze_content()

    # Display comprehensive results
    print("📊 COMPREHENSIVE ANALYSIS RESULTS:")
    print()

    print("📁 File Information:")
    print(f"   Path: {analysis['file_path']}")
    print(f"   Size: {analysis['file_size']:,} bytes")
    print()

    print("📄 PDF Content Analysis:")
    metrics = analysis['combined_metrics']
    print(f"   Text Length: {metrics['text_length']} characters")
    print(f"   Text per Page: {metrics['text_per_page']:.1f} chars/page")
    print(f"   Image Count: {metrics['image_count']}")
    print(f"   Table Count: {metrics['table_count']}")
    print(f"   Page Count: {metrics['page_count']}")
    print()

    print("🧠 Classification Factors:")
    factors = analysis['classification_factors']
    for factor, value in factors.items():
        icon = "✅" if value else "❌" if isinstance(value, bool) else "📊"
        print(f"   {icon} {factor}: {value}")
    print()

    print("🎯 Classification Result:")
    print(f"   Recommended Type: Type {analysis['recommended_type']}")
    print(f"   Confidence Score: {analysis['confidence_score']:.2f}")
    print(f"   Manual Review Needed: {'⚠️ YES' if analysis['manual_review_needed'] else '✅ NO'}")
    print()

    if metrics['sample_text']:
        print("📝 Sample Text (first 200 chars):")
        print(f"   {repr(metrics['sample_text'][:200])}")
        print()

    # Compare with current tracking.json classification
    try:
        with open('tracking.json', 'r') as f:
            tracking_data = json.load(f)

        current_type = None
        for pdf in tracking_data['pdfs']:
            if pdf['ac_number'] == ac_number:
                current_type = pdf['pdf_type']
                break

        print("🔄 Comparison with Current Classification:")
        print(f"   Current Type: Type {current_type}")
        print(f"   New Recommendation: Type {analysis['recommended_type']}")
        if current_type != analysis['recommended_type']:
            print(f"   🚨 CLASSIFICATION CHANGE RECOMMENDED")
        else:
            print(f"   ✅ Classification confirmed")

    except Exception as e:
        print(f"   ⚠️ Could not compare with tracking.json: {e}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python test_single_classification.py <AC_NUMBER>")
        print("Example: python test_single_classification.py 8")
        sys.exit(1)

    try:
        ac_number = int(sys.argv[1])
        test_single_pdf(ac_number)
    except ValueError:
        print("Error: AC number must be an integer")
        sys.exit(1)