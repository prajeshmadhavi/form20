#!/usr/bin/env python3
"""
PDF Classifier for Form 20 Documents
Automatically classifies PDFs into extraction tiers based on content analysis
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

try:
    import fitz  # PyMuPDF
    from PIL import Image
    import numpy as np
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install PyMuPDF pillow numpy")
    exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFClassifier:
    """Classify PDFs into extraction tiers"""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.classification_file = self.base_dir / "tracking/pdf_classification.json"
        self.classifications = {}

    def classify_all_pdfs(self, force: bool = False):
        """Classify all PDFs in VIDHANSABHA_2024 directory"""
        vidhansabha_dir = self.base_dir / "VIDHANSABHA_2024"

        if not vidhansabha_dir.exists():
            logger.error(f"Directory not found: {vidhansabha_dir}")
            return

        # Load existing classifications if not forcing
        if self.classification_file.exists() and not force:
            with open(self.classification_file, 'r') as f:
                self.classifications = json.load(f)
            logger.info(f"Loaded existing classifications for {len(self.classifications)} PDFs")

        pdf_files = []
        for district_dir in vidhansabha_dir.iterdir():
            if district_dir.is_dir():
                pdf_files.extend(district_dir.glob("*.pdf"))

        logger.info(f"Found {len(pdf_files)} PDFs to classify")

        for pdf_path in pdf_files:
            ac_number = pdf_path.stem

            if ac_number in self.classifications and not force:
                logger.debug(f"Skipping already classified: {ac_number}")
                continue

            logger.info(f"Classifying {ac_number}...")
            classification = self.classify_single_pdf(pdf_path)
            self.classifications[ac_number] = classification

            # Save progress every 10 PDFs
            if len(self.classifications) % 10 == 0:
                self.save_classifications()

        # Final save
        self.save_classifications()
        self.print_summary()

    def classify_single_pdf(self, pdf_path: Path) -> Dict:
        """Classify a single PDF into extraction tier"""
        classification = {
            "file_path": str(pdf_path.relative_to(self.base_dir)),
            "district": pdf_path.parent.name,
            "tier": None,
            "characteristics": {},
            "confidence": 0.0,
            "extraction_method": None
        }

        try:
            doc = fitz.open(str(pdf_path))

            # Analyze PDF characteristics
            analysis = self.analyze_pdf(doc)
            classification["characteristics"] = analysis

            # Determine tier based on analysis
            tier, confidence, method = self.determine_tier(analysis)
            classification["tier"] = tier
            classification["confidence"] = confidence
            classification["extraction_method"] = method

            doc.close()

        except Exception as e:
            logger.error(f"Failed to classify {pdf_path}: {e}")
            classification["tier"] = 3  # Default to OCR for problematic PDFs
            classification["extraction_method"] = "OCR"
            classification["error"] = str(e)

        return classification

    def analyze_pdf(self, doc: fitz.Document) -> Dict:
        """Analyze PDF characteristics"""
        analysis = {
            "page_count": len(doc),
            "has_text": False,
            "text_percentage": 0.0,
            "has_images": False,
            "image_percentage": 0.0,
            "is_scanned": False,
            "has_tables": False,
            "language": "unknown",
            "has_devanagari": False,
            "rotation_detected": False,
            "average_font_size": 0,
            "text_extraction_quality": "unknown"
        }

        total_text = []
        total_area = 0
        text_area = 0
        image_area = 0

        for page_num in range(min(5, len(doc))):  # Analyze first 5 pages
            page = doc[page_num]
            page_rect = page.rect
            total_area += page_rect.width * page_rect.height

            # Extract text
            text = page.get_text()
            total_text.append(text)

            if text and len(text.strip()) > 50:
                analysis["has_text"] = True
                # Estimate text area
                text_blocks = page.get_text("blocks")
                for block in text_blocks:
                    if block[6] == 0:  # Text block
                        block_area = (block[2] - block[0]) * (block[3] - block[1])
                        text_area += block_area

            # Check for images
            image_list = page.get_images()
            if image_list:
                analysis["has_images"] = True
                for img in image_list:
                    # Get image area
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    image_area += pix.width * pix.height
                    pix = None

            # Check rotation
            if abs(page.rotation) > 0:
                analysis["rotation_detected"] = True

        # Calculate percentages
        if total_area > 0:
            analysis["text_percentage"] = (text_area / total_area) * 100
            analysis["image_percentage"] = (image_area / total_area) * 100

        # Analyze text content
        combined_text = '\n'.join(total_text)

        if combined_text:
            # Check for Devanagari script
            devanagari_pattern = r'[\u0900-\u097F]'
            if re.search(devanagari_pattern, combined_text):
                analysis["has_devanagari"] = True

            # Check for tables
            table_indicators = ['Total', 'Serial', 'Votes', 'NOTA', 'Rejected']
            if any(indicator in combined_text for indicator in table_indicators):
                analysis["has_tables"] = True

            # Determine language
            if analysis["has_devanagari"]:
                english_words = len(re.findall(r'[a-zA-Z]+', combined_text))
                devanagari_words = len(re.findall(r'[\u0900-\u097F]+', combined_text))

                if english_words > devanagari_words * 2:
                    analysis["language"] = "english_primary"
                elif devanagari_words > english_words:
                    analysis["language"] = "devanagari_primary"
                else:
                    analysis["language"] = "mixed"
            else:
                analysis["language"] = "english"

            # Assess text extraction quality
            if len(combined_text) > 1000:
                # Check for garbled text (common in bad OCR)
                garbled_indicators = ['�', '□', '???']
                garbled_count = sum(combined_text.count(ind) for ind in garbled_indicators)

                if garbled_count > len(combined_text) * 0.1:
                    analysis["text_extraction_quality"] = "poor"
                elif garbled_count > len(combined_text) * 0.05:
                    analysis["text_extraction_quality"] = "medium"
                else:
                    analysis["text_extraction_quality"] = "good"

        # Determine if scanned
        if (analysis["has_images"] and
            not analysis["has_text"] or
            analysis["text_percentage"] < 5):
            analysis["is_scanned"] = True

        return analysis

    def determine_tier(self, analysis: Dict) -> Tuple[int, float, str]:
        """Determine extraction tier based on PDF analysis"""

        # Tier 1: Standard English PDFs with good text extraction
        if (analysis["has_text"] and
            analysis["text_extraction_quality"] in ["good", "medium"] and
            analysis["language"] in ["english", "english_primary"] and
            not analysis["rotation_detected"] and
            not analysis["is_scanned"]):

            confidence = 0.95 if analysis["text_extraction_quality"] == "good" else 0.85
            return 1, confidence, "standard_extraction"

        # Tier 2: PDFs with Devanagari text but otherwise extractable
        elif (analysis["has_text"] and
              analysis["has_devanagari"] and
              not analysis["is_scanned"] and
              analysis["text_extraction_quality"] != "poor"):

            confidence = 0.8 if analysis["language"] == "mixed" else 0.75
            return 2, confidence, "devanagari_extraction"

        # Tier 3: Scanned, rotated, or poor quality PDFs requiring OCR
        else:
            confidence = 0.6 if analysis["has_images"] else 0.4
            return 3, confidence, "ocr_extraction"

    def save_classifications(self):
        """Save classifications to file"""
        self.classification_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.classification_file, 'w') as f:
            json.dump(self.classifications, f, indent=2)
        logger.info(f"Saved classifications for {len(self.classifications)} PDFs")

    def print_summary(self):
        """Print classification summary"""
        if not self.classifications:
            print("No PDFs classified yet")
            return

        tier_counts = {1: 0, 2: 0, 3: 0}
        district_stats = {}

        for ac_number, info in self.classifications.items():
            tier = info["tier"]
            district = info["district"]

            tier_counts[tier] = tier_counts.get(tier, 0) + 1

            if district not in district_stats:
                district_stats[district] = {1: 0, 2: 0, 3: 0}
            district_stats[district][tier] += 1

        print("\n" + "="*60)
        print("PDF CLASSIFICATION SUMMARY")
        print("="*60)
        print(f"Total PDFs: {len(self.classifications)}")
        print("\nTier Distribution:")
        print(f"  Tier 1 (Standard):    {tier_counts[1]:>3} ({tier_counts[1]/len(self.classifications)*100:.1f}%)")
        print(f"  Tier 2 (Devanagari):  {tier_counts[2]:>3} ({tier_counts[2]/len(self.classifications)*100:.1f}%)")
        print(f"  Tier 3 (OCR):         {tier_counts[3]:>3} ({tier_counts[3]/len(self.classifications)*100:.1f}%)")

        print("\nDistrict-wise Classification:")
        print("-"*60)
        print(f"{'District':<30} T1   T2   T3   Total")
        print("-"*60)

        for district in sorted(district_stats.keys()):
            stats = district_stats[district]
            total = sum(stats.values())
            print(f"{district:<30} {stats[1]:>3}  {stats[2]:>3}  {stats[3]:>3}   {total:>3}")

        print("="*60)

    def get_tier_recommendations(self):
        """Get processing recommendations based on classification"""
        recommendations = {
            "tier_1_batch_size": 10,
            "tier_2_batch_size": 5,
            "tier_3_batch_size": 2,
            "parallel_processing": {
                "tier_1": min(4, len([1 for c in self.classifications.values() if c["tier"] == 1]) // 10),
                "tier_2": min(2, len([1 for c in self.classifications.values() if c["tier"] == 2]) // 10),
                "tier_3": 1  # OCR is resource-intensive
            },
            "estimated_time": {
                "tier_1": len([1 for c in self.classifications.values() if c["tier"] == 1]) * 0.5,  # minutes
                "tier_2": len([1 for c in self.classifications.values() if c["tier"] == 2]) * 1,
                "tier_3": len([1 for c in self.classifications.values() if c["tier"] == 3]) * 3
            }
        }

        total_time = sum(recommendations["estimated_time"].values())
        recommendations["total_estimated_time"] = f"{total_time/60:.1f} hours"

        return recommendations

    def reclassify_pdf(self, ac_number: str, new_tier: int, reason: str = ""):
        """Manually reclassify a PDF"""
        if ac_number not in self.classifications:
            logger.error(f"PDF {ac_number} not found in classifications")
            return

        old_tier = self.classifications[ac_number]["tier"]
        self.classifications[ac_number]["tier"] = new_tier
        self.classifications[ac_number]["manual_override"] = True
        self.classifications[ac_number]["override_reason"] = reason
        self.classifications[ac_number]["original_tier"] = old_tier

        self.save_classifications()
        logger.info(f"Reclassified {ac_number} from Tier {old_tier} to Tier {new_tier}")

def main():
    import argparse

    parser = argparse.ArgumentParser(description="PDF Classifier for Form 20 Documents")
    parser.add_argument("--classify", action="store_true", help="Classify all PDFs")
    parser.add_argument("--force", action="store_true", help="Force reclassification")
    parser.add_argument("--summary", action="store_true", help="Show classification summary")
    parser.add_argument("--check", help="Check classification of specific PDF (e.g., AC_216)")
    parser.add_argument("--reclassify", help="Reclassify PDF (format: AC_216:2:reason)")
    parser.add_argument("--recommendations", action="store_true", help="Get processing recommendations")

    args = parser.parse_args()

    classifier = PDFClassifier()

    if args.classify:
        classifier.classify_all_pdfs(force=args.force)
    elif args.summary:
        # Load existing classifications
        if classifier.classification_file.exists():
            with open(classifier.classification_file, 'r') as f:
                classifier.classifications = json.load(f)
        classifier.print_summary()
    elif args.check:
        if classifier.classification_file.exists():
            with open(classifier.classification_file, 'r') as f:
                classifications = json.load(f)

            if args.check in classifications:
                info = classifications[args.check]
                print(f"\n{args.check} Classification:")
                print(f"  District: {info['district']}")
                print(f"  Tier: {info['tier']}")
                print(f"  Confidence: {info['confidence']:.2f}")
                print(f"  Method: {info['extraction_method']}")
                print("\n  Characteristics:")
                for key, value in info['characteristics'].items():
                    print(f"    {key}: {value}")
            else:
                print(f"{args.check} not found in classifications")
    elif args.reclassify:
        parts = args.reclassify.split(":")
        if len(parts) >= 2:
            ac_number, new_tier = parts[0], int(parts[1])
            reason = parts[2] if len(parts) > 2 else ""

            if classifier.classification_file.exists():
                with open(classifier.classification_file, 'r') as f:
                    classifier.classifications = json.load(f)

            classifier.reclassify_pdf(ac_number, new_tier, reason)
    elif args.recommendations:
        if classifier.classification_file.exists():
            with open(classifier.classification_file, 'r') as f:
                classifier.classifications = json.load(f)

        recs = classifier.get_tier_recommendations()
        print("\nProcessing Recommendations:")
        print(json.dumps(recs, indent=2))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()