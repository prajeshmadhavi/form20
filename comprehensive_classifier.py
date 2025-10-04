#!/usr/bin/env python3
"""
Comprehensive PDF Classifier for Form 20 Documents
Analyzes each PDF individually with detailed scoring and manual review capabilities
"""

import json
import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pdfplumber
import fitz
import pandas as pd
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('classification.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PDFAnalyzer:
    """Comprehensive PDF analysis with detailed scoring"""

    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path
        self.analysis_results = {}

    def analyze_content(self) -> Dict:
        """Perform comprehensive content analysis"""

        analysis = {
            'file_path': str(self.pdf_path),
            'file_size': self.pdf_path.stat().st_size if self.pdf_path.exists() else 0,
            'pdfplumber_results': {},
            'pymupdf_results': {},
            'combined_metrics': {},
            'classification_factors': {},
            'recommended_type': None,
            'confidence_score': 0.0,
            'manual_review_needed': False,
            'analysis_timestamp': datetime.now().isoformat()
        }

        # Analysis with pdfplumber
        analysis['pdfplumber_results'] = self._analyze_with_pdfplumber()

        # Analysis with PyMuPDF
        analysis['pymupdf_results'] = self._analyze_with_pymupdf()

        # Combine results and calculate metrics
        analysis['combined_metrics'] = self._calculate_combined_metrics(
            analysis['pdfplumber_results'],
            analysis['pymupdf_results']
        )

        # Determine classification factors
        analysis['classification_factors'] = self._analyze_classification_factors(
            analysis['combined_metrics']
        )

        # Make final classification
        analysis['recommended_type'], analysis['confidence_score'] = self._classify_pdf(
            analysis['classification_factors']
        )

        # Determine if manual review is needed
        analysis['manual_review_needed'] = self._needs_manual_review(
            analysis['confidence_score'],
            analysis['classification_factors']
        )

        return analysis

    def _analyze_with_pdfplumber(self) -> Dict:
        """Analyze PDF using pdfplumber"""
        results = {
            'success': False,
            'page_count': 0,
            'total_text_length': 0,
            'pages_with_text': 0,
            'total_tables': 0,
            'pages_with_tables': 0,
            'total_images': 0,
            'sample_text': '',
            'table_structure_quality': 0.0,
            'error': None
        }

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                results['page_count'] = len(pdf.pages)

                for i, page in enumerate(pdf.pages):
                    # Text analysis
                    text = page.extract_text()
                    if text and text.strip():
                        text_length = len(text.strip())
                        results['total_text_length'] += text_length
                        results['pages_with_text'] += 1

                        # Capture sample text from first page with substantial content
                        if not results['sample_text'] and text_length > 100:
                            results['sample_text'] = text[:500]

                    # Table analysis
                    try:
                        tables = page.extract_tables()
                        if tables:
                            table_count = len(tables)
                            results['total_tables'] += table_count
                            results['pages_with_tables'] += 1

                            # Assess table quality
                            for table in tables:
                                if table and len(table) > 2:  # At least 3 rows
                                    results['table_structure_quality'] += 1
                    except:
                        pass  # Table extraction might fail

                    # Image analysis
                    try:
                        if hasattr(page, 'images'):
                            results['total_images'] += len(page.images)
                    except:
                        pass

                results['success'] = True

        except Exception as e:
            results['error'] = str(e)
            logger.error(f"pdfplumber analysis failed for {self.pdf_path}: {e}")

        return results

    def _analyze_with_pymupdf(self) -> Dict:
        """Analyze PDF using PyMuPDF"""
        results = {
            'success': False,
            'page_count': 0,
            'total_text_length': 0,
            'pages_with_text': 0,
            'total_images': 0,
            'sample_text': '',
            'text_blocks_count': 0,
            'average_text_confidence': 0.0,
            'error': None
        }

        try:
            doc = fitz.open(self.pdf_path)
            results['page_count'] = len(doc)

            for page_num in range(len(doc)):
                page = doc[page_num]

                # Text analysis
                text = page.get_text()
                if text and text.strip():
                    text_length = len(text.strip())
                    results['total_text_length'] += text_length
                    results['pages_with_text'] += 1

                    if not results['sample_text'] and text_length > 100:
                        results['sample_text'] = text[:500]

                # Text blocks analysis
                try:
                    text_blocks = page.get_text("dict")
                    if text_blocks and 'blocks' in text_blocks:
                        results['text_blocks_count'] += len(text_blocks['blocks'])
                except:
                    pass

                # Image analysis
                try:
                    image_list = page.get_images()
                    results['total_images'] += len(image_list)
                except:
                    pass

            doc.close()
            results['success'] = True

        except Exception as e:
            results['error'] = str(e)
            logger.error(f"PyMuPDF analysis failed for {self.pdf_path}: {e}")

        return results

    def _calculate_combined_metrics(self, pdfplumber_results: Dict, pymupdf_results: Dict) -> Dict:
        """Calculate combined metrics from both analysis methods"""

        # Use the best results from either method
        best_text_length = max(
            pdfplumber_results.get('total_text_length', 0),
            pymupdf_results.get('total_text_length', 0)
        )

        best_sample_text = (
            pdfplumber_results.get('sample_text', '') or
            pymupdf_results.get('sample_text', '')
        )

        total_images = max(
            pdfplumber_results.get('total_images', 0),
            pymupdf_results.get('total_images', 0)
        )

        page_count = max(
            pdfplumber_results.get('page_count', 0),
            pymupdf_results.get('page_count', 0)
        )

        return {
            'text_length': best_text_length,
            'text_per_page': best_text_length / max(page_count, 1),
            'sample_text': best_sample_text,
            'image_count': total_images,
            'images_per_page': total_images / max(page_count, 1),
            'page_count': page_count,
            'table_count': pdfplumber_results.get('total_tables', 0),
            'table_structure_quality': pdfplumber_results.get('table_structure_quality', 0),
            'has_substantial_text': best_text_length > 500,
            'has_minimal_text': best_text_length < 100,
            'has_images': total_images > 0,
            'has_many_images': total_images > 5
        }

    def _analyze_classification_factors(self, metrics: Dict) -> Dict:
        """Analyze factors that influence classification"""

        factors = {}
        sample_text = metrics.get('sample_text', '')

        # Text quality factors
        factors['readable_text'] = metrics['text_length'] > 500
        factors['minimal_text'] = metrics['text_length'] < 100
        factors['garbled_text'] = self._detect_garbled_text(sample_text)
        factors['structured_content'] = metrics.get('table_count', 0) > 0

        # Language factors
        factors['non_ascii_ratio'] = self._calculate_non_ascii_ratio(sample_text)
        factors['has_devanagari'] = self._has_devanagari_script(sample_text)
        factors['primarily_english'] = factors['non_ascii_ratio'] < 0.1

        # Image factors
        factors['has_images'] = metrics['has_images']
        factors['image_heavy'] = metrics['has_many_images']
        factors['likely_scanned'] = (
            metrics['has_images'] and
            (metrics['has_minimal_text'] or factors['garbled_text'])
        )

        # Quality indicators
        factors['extraction_confidence'] = self._calculate_extraction_confidence(metrics, factors)

        return factors

    def _detect_garbled_text(self, text: str) -> bool:
        """Detect if text appears garbled or OCR-corrupted"""
        if not text:
            return False

        # Look for signs of garbled text
        garbled_indicators = [
            r'[oO0]{3,}',  # Multiple o's or 0's in sequence
            r'[-_|]{5,}',  # Multiple dashes/underscores
            r'[A-Z]{10,}', # Very long uppercase sequences
            r'\b[a-zA-Z]{1,2}\b.*\b[a-zA-Z]{1,2}\b.*\b[a-zA-Z]{1,2}\b', # Many single/double letter words
        ]

        garbled_count = 0
        for pattern in garbled_indicators:
            if re.search(pattern, text):
                garbled_count += 1

        # Check ratio of meaningful words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        total_chars = len(re.findall(r'[a-zA-Z]', text))

        if total_chars > 50:
            meaningful_ratio = len(' '.join(words)) / total_chars
            return garbled_count >= 2 or meaningful_ratio < 0.3

        return garbled_count >= 2

    def _calculate_non_ascii_ratio(self, text: str) -> float:
        """Calculate ratio of non-ASCII characters"""
        if not text:
            return 0.0

        non_ascii_chars = sum(1 for c in text if ord(c) > 127)
        total_chars = len(text)

        return non_ascii_chars / max(total_chars, 1)

    def _has_devanagari_script(self, text: str) -> bool:
        """Check if text contains Devanagari script"""
        devanagari_pattern = r'[\u0900-\u097F]'
        return bool(re.search(devanagari_pattern, text))

    def _calculate_extraction_confidence(self, metrics: Dict, factors: Dict) -> float:
        """Calculate confidence in text extraction quality"""
        confidence = 0.0

        # Text length factor
        if metrics['text_length'] > 2000:
            confidence += 0.4
        elif metrics['text_length'] > 500:
            confidence += 0.3
        elif metrics['text_length'] > 100:
            confidence += 0.1

        # Text quality factor
        if not factors['garbled_text']:
            confidence += 0.3

        # Structure factor
        if factors['structured_content']:
            confidence += 0.2

        # Image factor (negative for scanned docs)
        if factors['likely_scanned']:
            confidence -= 0.2

        return max(0.0, min(1.0, confidence))

    def _classify_pdf(self, factors: Dict) -> Tuple[int, float]:
        """Classify PDF based on analysis factors"""

        # Type 3 indicators (OCR required)
        type3_score = 0.0
        if factors['likely_scanned']:
            type3_score += 0.5
        if factors['minimal_text']:
            type3_score += 0.3
        if factors['garbled_text']:
            type3_score += 0.3
        if factors['has_images'] and not factors['readable_text']:
            type3_score += 0.2

        # Type 2 indicators (Local language)
        type2_score = 0.0
        if factors['has_devanagari']:
            type2_score += 0.6
        if factors['non_ascii_ratio'] > 0.15:
            type2_score += 0.4
        if factors['readable_text'] and not factors['primarily_english']:
            type2_score += 0.3

        # Type 1 indicators (Standard English)
        type1_score = 0.0
        if factors['readable_text']:
            type1_score += 0.4
        if factors['primarily_english']:
            type1_score += 0.3
        if factors['structured_content']:
            type1_score += 0.2
        if factors['extraction_confidence'] > 0.7:
            type1_score += 0.3

        # Determine classification
        scores = {1: type1_score, 2: type2_score, 3: type3_score}
        recommended_type = max(scores, key=scores.get)
        confidence = scores[recommended_type]

        return recommended_type, confidence

    def _needs_manual_review(self, confidence: float, factors: Dict) -> bool:
        """Determine if manual review is needed"""
        return (
            confidence < 0.6 or  # Low confidence
            factors['extraction_confidence'] < 0.5 or  # Poor extraction
            (factors['has_images'] and factors['readable_text'])  # Borderline case
        )

class ComprehensiveClassifier:
    """Main classifier that processes all PDFs"""

    def __init__(self, base_dir: str = "VIDHANSABHA_2024"):
        self.base_dir = Path(base_dir)
        self.results = []
        self.output_file = "comprehensive_classification_results.json"

    def find_all_pdfs(self) -> List[Path]:
        """Find all PDF files"""
        return list(self.base_dir.glob("**/*.pdf"))

    def classify_all_pdfs(self, start_from: int = 0, interactive: bool = True) -> List[Dict]:
        """Classify all PDFs with optional interactive review"""

        pdf_files = self.find_all_pdfs()
        print(f"Found {len(pdf_files)} PDF files")

        if start_from > 0:
            pdf_files = pdf_files[start_from:]
            print(f"Starting from PDF #{start_from + 1}")

        for i, pdf_path in enumerate(pdf_files):
            current_num = start_from + i + 1
            print(f"\n{'='*60}")
            print(f"Processing {current_num}/{len(pdf_files) + start_from}: {pdf_path.name}")
            print(f"Path: {pdf_path}")

            # Extract AC number
            ac_match = re.search(r'AC_(\d+)\.pdf', pdf_path.name)
            ac_number = int(ac_match.group(1)) if ac_match else None

            # Analyze PDF
            analyzer = PDFAnalyzer(pdf_path)
            analysis = analyzer.analyze_content()
            analysis['ac_number'] = ac_number
            analysis['processing_order'] = current_num

            # Display results
            self._display_analysis_results(analysis)

            # Interactive review if needed
            if interactive and analysis['manual_review_needed']:
                final_type = self._interactive_review(analysis)
                if final_type is not None:
                    analysis['final_type'] = final_type
                    analysis['manual_override'] = True
                else:
                    analysis['final_type'] = analysis['recommended_type']
                    analysis['manual_override'] = False
            else:
                analysis['final_type'] = analysis['recommended_type']
                analysis['manual_override'] = False

            self.results.append(analysis)

            # Save progress every 10 PDFs
            if current_num % 10 == 0:
                self._save_results()
                print(f"\n✅ Progress saved after {current_num} PDFs")

            # Interactive control
            if interactive:
                choice = input("\nContinue? (y)es/(n)o/(s)kip to end: ").lower()
                if choice == 'n':
                    break
                elif choice == 's':
                    interactive = False

        # Final save
        self._save_results()
        self._generate_summary_report()

        return self.results

    def _display_analysis_results(self, analysis: Dict):
        """Display analysis results in a readable format"""

        print(f"📊 Analysis Results:")
        print(f"   File Size: {analysis['file_size']:,} bytes")

        metrics = analysis['combined_metrics']
        print(f"   Text Length: {metrics['text_length']} chars")
        print(f"   Images: {metrics['image_count']}")
        print(f"   Tables: {metrics['table_count']}")

        factors = analysis['classification_factors']
        print(f"   Readable Text: {'✅' if factors['readable_text'] else '❌'}")
        print(f"   Garbled Text: {'⚠️' if factors['garbled_text'] else '✅'}")
        print(f"   Has Images: {'⚠️' if factors['has_images'] else '✅'}")
        print(f"   Extraction Confidence: {factors['extraction_confidence']:.2f}")

        print(f"🎯 Recommendation:")
        print(f"   Type: {analysis['recommended_type']}")
        print(f"   Confidence: {analysis['confidence_score']:.2f}")
        print(f"   Manual Review: {'⚠️ YES' if analysis['manual_review_needed'] else '✅ NO'}")

        if metrics['sample_text']:
            print(f"📝 Sample Text: {metrics['sample_text'][:100]}...")

    def _interactive_review(self, analysis: Dict) -> Optional[int]:
        """Interactive manual review for borderline cases"""

        print(f"\n🔍 MANUAL REVIEW NEEDED")
        print(f"Recommended Type: {analysis['recommended_type']}")
        print(f"Confidence: {analysis['confidence_score']:.2f}")

        while True:
            choice = input("Accept recommendation? (y)es/(1)Type1/(2)Type2/(3)Type3/(i)nfo: ").lower()

            if choice == 'y':
                return None  # Accept recommendation
            elif choice == '1':
                return 1
            elif choice == '2':
                return 2
            elif choice == '3':
                return 3
            elif choice == 'i':
                self._show_detailed_info(analysis)
            else:
                print("Invalid choice. Please try again.")

    def _show_detailed_info(self, analysis: Dict):
        """Show detailed analysis information"""
        print("\n📋 DETAILED ANALYSIS:")

        print("Combined Metrics:")
        for key, value in analysis['combined_metrics'].items():
            print(f"  {key}: {value}")

        print("\nClassification Factors:")
        for key, value in analysis['classification_factors'].items():
            print(f"  {key}: {value}")

    def _save_results(self):
        """Save results to JSON file"""
        with open(self.output_file, 'w') as f:
            json.dump({
                'classification_results': self.results,
                'summary': self._calculate_summary(),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)

    def _calculate_summary(self) -> Dict:
        """Calculate summary statistics"""
        if not self.results:
            return {}

        total = len(self.results)
        type_counts = {}
        confidence_sum = 0
        manual_overrides = 0

        for result in self.results:
            final_type = result.get('final_type', result['recommended_type'])
            type_counts[final_type] = type_counts.get(final_type, 0) + 1
            confidence_sum += result['confidence_score']
            if result.get('manual_override', False):
                manual_overrides += 1

        return {
            'total_pdfs': total,
            'type_distribution': type_counts,
            'average_confidence': confidence_sum / total,
            'manual_overrides': manual_overrides,
            'manual_override_rate': manual_overrides / total
        }

    def _generate_summary_report(self):
        """Generate a summary report"""
        summary = self._calculate_summary()

        print(f"\n{'='*60}")
        print("📊 CLASSIFICATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total PDFs Classified: {summary['total_pdfs']}")
        print(f"Average Confidence: {summary['average_confidence']:.2f}")
        print(f"Manual Overrides: {summary['manual_overrides']} ({summary['manual_override_rate']:.1%})")
        print()
        print("Type Distribution:")
        for pdf_type, count in summary['type_distribution'].items():
            percentage = count / summary['total_pdfs'] * 100
            print(f"  Type {pdf_type}: {count} PDFs ({percentage:.1f}%)")

        print(f"\n💾 Detailed results saved to: {self.output_file}")

def main():
    """Main execution function"""
    import argparse

    parser = argparse.ArgumentParser(description="Comprehensive PDF Classifier")
    parser.add_argument("--start-from", type=int, default=0, help="Start from PDF number")
    parser.add_argument("--non-interactive", action="store_true", help="Run without manual review")
    parser.add_argument("--base-dir", default="VIDHANSABHA_2024", help="Base directory for PDFs")

    args = parser.parse_args()

    print("Comprehensive PDF Classifier for Form 20 Documents")
    print("="*60)

    classifier = ComprehensiveClassifier(args.base_dir)
    results = classifier.classify_all_pdfs(
        start_from=args.start_from,
        interactive=not args.non_interactive
    )

    print("\n✅ Classification completed!")

if __name__ == "__main__":
    main()