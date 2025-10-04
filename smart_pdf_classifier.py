#!/usr/bin/env python3
"""
Smart PDF Classifier - Analyzes actual PDF content to determine type
Rather than relying on district names, this analyzes the PDF content
"""
import json
import pdfplumber
import fitz
from pathlib import Path
import re

def analyze_pdf_content(pdf_path):
    """Analyze PDF content to determine the correct type"""

    try:
        # Test 1: Try text extraction with pdfplumber
        text_length = 0
        images_count = 0

        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) > 0:
                page = pdf.pages[0]  # Test first page
                text = page.extract_text()
                text_length = len(text.strip()) if text else 0

                # Check for images
                try:
                    images_count = len(page.images)
                except:
                    images_count = 0

        # Test 2: Try with PyMuPDF for additional verification
        fitz_text_length = 0
        fitz_images_count = 0

        try:
            doc = fitz.open(pdf_path)
            if len(doc) > 0:
                page = doc[0]
                fitz_text = page.get_text()
                fitz_text_length = len(fitz_text.strip())
                fitz_images_count = len(page.get_images())
            doc.close()
        except:
            pass

        # Use the method that found more content
        final_text_length = max(text_length, fitz_text_length)
        final_images_count = max(images_count, fitz_images_count)

        # Classification logic based on content analysis
        if final_text_length == 0 or final_text_length < 50:
            # No text or very little text = Image-based PDF
            return 3, f"No text ({final_text_length} chars), {final_images_count} images - OCR required"

        elif final_images_count > 0 and final_text_length < 500:
            # Some images and limited text = Likely scanned
            return 3, f"Limited text ({final_text_length} chars), {final_images_count} images - OCR required"

        elif final_text_length > 500:
            # Good amount of text extracted
            # Check for non-English characters (Devanagari, etc.)
            non_ascii_chars = sum(1 for c in text[:1000] if ord(c) > 127) if text else 0
            non_ascii_ratio = non_ascii_chars / min(1000, len(text)) if text else 0

            if non_ascii_ratio > 0.1:  # More than 10% non-ASCII characters
                return 2, f"Text with local language ({final_text_length} chars, {non_ascii_ratio:.1%} non-ASCII)"
            else:
                return 1, f"Standard English text ({final_text_length} chars)"

        else:
            # Default fallback
            return 1, f"Default classification ({final_text_length} chars, {final_images_count} images)"

    except Exception as e:
        # If analysis fails, assume it needs OCR
        return 3, f"Analysis failed: {str(e)} - defaulting to OCR"

def reclassify_all_pdfs():
    """Reclassify all PDFs based on actual content analysis"""

    try:
        with open('tracking.json', 'r') as f:
            tracking_data = json.load(f)

        print("Reclassifying PDFs based on actual content analysis...")
        print("This may take a while as we analyze each PDF...")

        reclassified_count = 0
        type_changes = []

        for i, pdf_record in enumerate(tracking_data['pdfs']):
            pdf_path = Path(pdf_record['pdf_path'])
            ac_number = pdf_record['ac_number']
            old_type = pdf_record['pdf_type']

            print(f"Analyzing {i+1}/{len(tracking_data['pdfs'])}: AC_{ac_number} ({pdf_path.name})")

            if pdf_path.exists():
                new_type, reason = analyze_pdf_content(pdf_path)

                if new_type != old_type:
                    pdf_record['pdf_type'] = new_type
                    pdf_record['pdf_type_description'] = {
                        1: "Type 1 - Standard English Format",
                        2: "Type 2 - Local Language Format",
                        3: "Type 3 - Scanned/Image Format"
                    }[new_type]

                    reclassified_count += 1
                    type_changes.append({
                        'ac_number': ac_number,
                        'old_type': old_type,
                        'new_type': new_type,
                        'reason': reason,
                        'file': pdf_path.name
                    })

                    print(f"  RECLASSIFIED: Type {old_type} → Type {new_type} ({reason})")
                else:
                    print(f"  CONFIRMED: Type {new_type} ({reason})")
            else:
                print(f"  WARNING: File not found: {pdf_path}")

        # Update summary counts
        type1_count = sum(1 for p in tracking_data['pdfs'] if p['pdf_type'] == 1)
        type2_count = sum(1 for p in tracking_data['pdfs'] if p['pdf_type'] == 2)
        type3_count = sum(1 for p in tracking_data['pdfs'] if p['pdf_type'] == 3)

        tracking_data['summary']['type1_count'] = type1_count
        tracking_data['summary']['type2_count'] = type2_count
        tracking_data['summary']['type3_count'] = type3_count
        tracking_data['summary']['last_updated'] = '2024-09-26T01:30:00Z'

        # Save updated data
        with open('tracking.json', 'w') as f:
            json.dump(tracking_data, f, indent=2)

        print(f"\n✅ Reclassification Complete!")
        print(f"📊 Updated PDF type counts:")
        print(f"   Type 1 (Standard): {type1_count}")
        print(f"   Type 2 (Local Language): {type2_count}")
        print(f"   Type 3 (OCR Required): {type3_count}")
        print(f"   Total Reclassified: {reclassified_count}")

        if type_changes:
            print(f"\n🔄 Key Reclassifications:")
            for change in type_changes[:10]:  # Show first 10 changes
                print(f"   AC_{change['ac_number']}: Type {change['old_type']} → Type {change['new_type']} ({change['reason'][:60]}...)")

        return type_changes

    except Exception as e:
        print(f"Error reclassifying PDFs: {e}")
        return []

if __name__ == "__main__":
    print("Smart PDF Content-Based Classifier")
    print("=" * 50)

    # Test single PDF first
    test_pdf = "VIDHANSABHA_2024/Nandurbar/AC_01.pdf"
    if Path(test_pdf).exists():
        print(f"Testing: {test_pdf}")
        pdf_type, reason = analyze_pdf_content(test_pdf)
        print(f"Result: Type {pdf_type} - {reason}")
        print()

    # Ask for confirmation before reclassifying all
    response = input("Reclassify all 287 PDFs based on content analysis? (y/n): ")
    if response.lower() == 'y':
        reclassify_all_pdfs()
    else:
        print("Reclassification cancelled.")