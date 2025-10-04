#!/usr/bin/env python3
"""
Analyze the 20 low-quality Type 1 PDFs to understand failure patterns
"""
import json
import pdfplumber
import fitz
from pathlib import Path

def analyze_failed_pdf(ac_number):
    """Analyze why a specific PDF failed extraction"""

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
        return {
            'ac_number': ac_number,
            'error': 'PDF file not found',
            'analysis': {}
        }

    analysis = {
        'ac_number': ac_number,
        'pdf_path': str(pdf_path),
        'file_size': pdf_path.stat().st_size,
        'pdfplumber_analysis': {},
        'pymupdf_analysis': {},
        'classification_check': {},
        'table_structure': {},
        'recommendation': ''
    }

    # Analyze with pdfplumber
    try:
        with pdfplumber.open(pdf_path) as pdf:
            analysis['pdfplumber_analysis'] = {
                'page_count': len(pdf.pages),
                'total_text_length': 0,
                'tables_found': 0,
                'images_found': 0,
                'sample_text': ''
            }

            for i, page in enumerate(pdf.pages[:3]):  # Check first 3 pages
                text = page.extract_text()
                if text:
                    analysis['pdfplumber_analysis']['total_text_length'] += len(text)
                    if not analysis['pdfplumber_analysis']['sample_text']:
                        analysis['pdfplumber_analysis']['sample_text'] = text[:500]

                tables = page.extract_tables()
                if tables:
                    analysis['pdfplumber_analysis']['tables_found'] += len(tables)

                    # Analyze table structure
                    for table_num, table in enumerate(tables):
                        if table and len(table) > 1:
                            table_key = f'page_{i+1}_table_{table_num+1}'
                            analysis['table_structure'][table_key] = {
                                'rows': len(table),
                                'columns': len(table[0]) if table[0] else 0,
                                'sample_data': table[:3] if len(table) >= 3 else table
                            }

                try:
                    if hasattr(page, 'images'):
                        analysis['pdfplumber_analysis']['images_found'] += len(page.images)
                except:
                    pass

    except Exception as e:
        analysis['pdfplumber_analysis']['error'] = str(e)

    # Analyze with PyMuPDF
    try:
        doc = fitz.open(pdf_path)
        analysis['pymupdf_analysis'] = {
            'page_count': len(doc),
            'total_text_length': 0,
            'images_found': 0
        }

        for page_num in range(min(3, len(doc))):  # Check first 3 pages
            page = doc[page_num]
            text = page.get_text()
            if text:
                analysis['pymupdf_analysis']['total_text_length'] += len(text)

            try:
                image_list = page.get_images()
                analysis['pymupdf_analysis']['images_found'] += len(image_list)
            except:
                pass

        doc.close()

    except Exception as e:
        analysis['pymupdf_analysis']['error'] = str(e)

    # Classification check
    pdfplumber_text = analysis['pdfplumber_analysis'].get('total_text_length', 0)
    pymupdf_text = analysis['pymupdf_analysis'].get('total_text_length', 0)
    best_text_length = max(pdfplumber_text, pymupdf_text)

    pdfplumber_images = analysis['pdfplumber_analysis'].get('images_found', 0)
    pymupdf_images = analysis['pymupdf_analysis'].get('images_found', 0)
    total_images = max(pdfplumber_images, pymupdf_images)

    # Determine if misclassified
    if best_text_length < 100 or (total_images > 5 and best_text_length < 1000):
        analysis['classification_check']['should_be_type'] = 3
        analysis['classification_check']['reason'] = f"Low text ({best_text_length} chars), {total_images} images - needs OCR"
    elif best_text_length > 500 and total_images == 0:
        analysis['classification_check']['should_be_type'] = 1
        analysis['classification_check']['reason'] = f"Good text ({best_text_length} chars), no images - should work as Type 1"
    else:
        analysis['classification_check']['should_be_type'] = 1
        analysis['classification_check']['reason'] = f"Borderline: {best_text_length} chars text, {total_images} images"

    # Recommendation
    tables_found = analysis['pdfplumber_analysis'].get('tables_found', 0)
    if analysis['classification_check']['should_be_type'] == 3:
        analysis['recommendation'] = 'RECLASSIFY_TO_TYPE_3'
    elif tables_found == 0:
        analysis['recommendation'] = 'ENHANCED_TABLE_EXTRACTION'
    else:
        analysis['recommendation'] = 'IMPROVE_TYPE1_LOGIC'

    return analysis

def analyze_all_failed_type1():
    """Analyze all 20 low-quality Type 1 PDFs"""

    low_quality_acs = [27, 30, 35, 39, 49, 52, 62, 79, 104, 121, 154, 162, 168, 178, 191, 215, 243, 265, 272, 281]

    print("=== ANALYZING 20 LOW-QUALITY TYPE 1 PDFS ===")
    print()

    results = []
    reclassify_to_type3 = []
    enhance_table_extraction = []
    improve_type1_logic = []

    for ac_number in low_quality_acs:
        print(f"Analyzing AC_{ac_number}...")
        analysis = analyze_failed_pdf(ac_number)
        results.append(analysis)

        # Categorize by recommendation
        recommendation = analysis.get('recommendation', 'UNKNOWN')
        if recommendation == 'RECLASSIFY_TO_TYPE_3':
            reclassify_to_type3.append(ac_number)
        elif recommendation == 'ENHANCED_TABLE_EXTRACTION':
            enhance_table_extraction.append(ac_number)
        else:
            improve_type1_logic.append(ac_number)

        # Show brief analysis
        pdfplumber_text = analysis.get('pdfplumber_analysis', {}).get('total_text_length', 0)
        images = analysis.get('pdfplumber_analysis', {}).get('images_found', 0)
        tables = analysis.get('pdfplumber_analysis', {}).get('tables_found', 0)

        print(f"  Text: {pdfplumber_text} chars, Images: {images}, Tables: {tables}")
        print(f"  Recommendation: {recommendation}")
        print()

    # Summary
    print("=" * 60)
    print("📊 FAILURE ANALYSIS SUMMARY")
    print("=" * 60)

    print(f"🔄 RECLASSIFY TO TYPE 3: {len(reclassify_to_type3)} PDFs")
    if reclassify_to_type3:
        print(f"   ACs: {reclassify_to_type3}")
        print("   Reason: Low text, high images - actually need OCR")

    print(f"🔧 ENHANCE TABLE EXTRACTION: {len(enhance_table_extraction)} PDFs")
    if enhance_table_extraction:
        print(f"   ACs: {enhance_table_extraction}")
        print("   Reason: No tables detected - different structure")

    print(f"⚙️ IMPROVE TYPE 1 LOGIC: {len(improve_type1_logic)} PDFs")
    if improve_type1_logic:
        print(f"   ACs: {improve_type1_logic}")
        print("   Reason: Tables found but extraction failed")

    # Save detailed analysis
    with open('failed_type1_analysis.json', 'w') as f:
        json.dump({
            'analysis_results': results,
            'categorization': {
                'reclassify_to_type3': reclassify_to_type3,
                'enhance_table_extraction': enhance_table_extraction,
                'improve_type1_logic': improve_type1_logic
            }
        }, f, indent=2)

    print(f"\n💾 Detailed analysis saved to: failed_type1_analysis.json")

    return results

if __name__ == "__main__":
    analyze_all_failed_type1()