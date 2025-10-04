#!/usr/bin/env python3
"""
Main Form 20 PDF Extraction Controller
Handles orchestration of tiered extraction with progress tracking and quality control
"""

import json
import os
import sys
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Form20Extractor:
    def __init__(self, config_path: str = "config/extraction_config.json"):
        """Initialize the extraction system"""
        self.base_dir = Path(__file__).parent.parent
        self.config = self.load_config(config_path)
        self.progress = self.load_progress()
        self.pdf_classification = self.load_classification()

    def load_config(self, config_path: str) -> Dict:
        """Load extraction configuration"""
        config_file = self.base_dir / config_path
        if not config_file.exists():
            # Create default config
            default_config = {
                "max_retries": 3,
                "timeout_seconds": 300,
                "batch_size": 10,
                "parallel_processing": {
                    "tier_1": 4,
                    "tier_2": 2,
                    "tier_3": 1
                },
                "quality_threshold": 0.85,
                "checkpoint_interval": 10
            }
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config

        with open(config_file, 'r') as f:
            return json.load(f)

    def load_progress(self) -> Dict:
        """Load or initialize progress tracking"""
        progress_file = self.base_dir / "tracking/extraction_progress.json"
        if not progress_file.exists():
            # Initialize progress tracking
            progress = {
                "total_pdfs": 287,
                "processed": 0,
                "pending": 287,
                "failed": 0,
                "manual_review": 0,
                "last_processed": None,
                "start_time": None,
                "pdfs": {}
            }
            # Initialize PDF entries
            self.initialize_pdf_tracking(progress)
            progress_file.parent.mkdir(parents=True, exist_ok=True)
            with open(progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
            return progress

        with open(progress_file, 'r') as f:
            return json.load(f)

    def load_classification(self) -> Dict:
        """Load PDF classification data"""
        classification_file = self.base_dir / "tracking/pdf_classification.json"
        if not classification_file.exists():
            logger.warning("PDF classification not found. Run pdf_classifier.py first.")
            return {}

        with open(classification_file, 'r') as f:
            return json.load(f)

    def initialize_pdf_tracking(self, progress: Dict):
        """Initialize tracking for all PDFs"""
        vidhansabha_dir = self.base_dir / "VIDHANSABHA_2024"
        pdf_id = 1

        for district_dir in sorted(vidhansabha_dir.iterdir()):
            if district_dir.is_dir():
                for pdf_file in sorted(district_dir.glob("*.pdf")):
                    ac_number = pdf_file.stem
                    progress["pdfs"][ac_number] = {
                        "id": pdf_id,
                        "district": district_dir.name,
                        "file_path": str(pdf_file.relative_to(self.base_dir)),
                        "tier": None,  # Will be set by classifier
                        "status": "pending",
                        "extraction_timestamp": None,
                        "record_count": None,
                        "quality_score": None,
                        "manual_verified": False,
                        "errors": [],
                        "retry_count": 0
                    }
                    pdf_id += 1

    def save_progress(self):
        """Save current progress state"""
        progress_file = self.base_dir / "tracking/extraction_progress.json"
        with open(progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)

    def get_next_pending_pdf(self) -> Optional[str]:
        """Get the next PDF to process"""
        for ac_number, pdf_info in self.progress["pdfs"].items():
            if pdf_info["status"] == "pending":
                return ac_number
        return None

    def extract_pdf(self, ac_number: str) -> Tuple[bool, Dict]:
        """Extract data from a single PDF based on its tier"""
        pdf_info = self.progress["pdfs"][ac_number]
        pdf_path = self.base_dir / pdf_info["file_path"]

        # Get tier from classification
        tier = self.pdf_classification.get(ac_number, {}).get("tier", 1)
        pdf_info["tier"] = tier

        logger.info(f"Processing {ac_number} (Tier {tier}): {pdf_path}")

        try:
            if tier == 1:
                from standard_extractor import StandardExtractor
                extractor = StandardExtractor()
                result = extractor.extract(pdf_path)
            elif tier == 2:
                from devanagari_extractor import DevanagariExtractor
                extractor = DevanagariExtractor()
                result = extractor.extract(pdf_path)
            elif tier == 3:
                from ocr_extractor import OCRExtractor
                extractor = OCRExtractor()
                result = extractor.extract(pdf_path)
            else:
                raise ValueError(f"Unknown tier: {tier}")

            # Validate extraction
            validation_result = self.validate_extraction(result)

            if validation_result["is_valid"]:
                pdf_info["status"] = "completed"
                pdf_info["record_count"] = result["record_count"]
                pdf_info["quality_score"] = validation_result["quality_score"]
                pdf_info["extraction_timestamp"] = datetime.now().isoformat()

                # Save extracted data
                self.save_extracted_data(ac_number, result)

                logger.info(f"✓ Successfully extracted {ac_number}: {result['record_count']} records (Q: {validation_result['quality_score']:.2f})")
                return True, result
            else:
                if validation_result["quality_score"] < self.config["quality_threshold"]:
                    pdf_info["status"] = "manual_review"
                    pdf_info["quality_score"] = validation_result["quality_score"]
                    logger.warning(f"⚠ {ac_number} needs manual review (Q: {validation_result['quality_score']:.2f})")
                else:
                    pdf_info["status"] = "failed"
                    pdf_info["errors"].append(validation_result["errors"])
                    logger.error(f"✗ Validation failed for {ac_number}: {validation_result['errors']}")

                return False, validation_result

        except Exception as e:
            error_msg = f"Extraction error: {str(e)}"
            logger.error(f"✗ Failed to extract {ac_number}: {error_msg}")
            pdf_info["errors"].append({
                "timestamp": datetime.now().isoformat(),
                "error": error_msg,
                "traceback": traceback.format_exc()
            })

            # Retry logic
            pdf_info["retry_count"] += 1
            if pdf_info["retry_count"] < self.config["max_retries"]:
                pdf_info["status"] = "pending"  # Will retry
                logger.info(f"Will retry {ac_number} (attempt {pdf_info['retry_count']}/{self.config['max_retries']})")
            else:
                pdf_info["status"] = "failed"
                logger.error(f"Max retries exceeded for {ac_number}")

            return False, {"error": error_msg}

    def validate_extraction(self, result: Dict) -> Dict:
        """Validate extracted data"""
        from validator import Validator
        validator = Validator()
        return validator.validate(result)

    def save_extracted_data(self, ac_number: str, result: Dict):
        """Save extracted data to output directory"""
        output_dir = self.base_dir / "output/extracted_data"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save raw JSON
        json_file = output_dir / f"{ac_number}_raw.json"
        with open(json_file, 'w') as f:
            json.dump(result, f, indent=2)

        # Save CSV
        csv_file = output_dir / f"{ac_number}.csv"
        self.save_as_csv(result, csv_file)

    def save_as_csv(self, result: Dict, csv_file: Path):
        """Convert and save result as CSV"""
        import csv

        with open(csv_file, 'w', newline='') as f:
            if result.get("records"):
                fieldnames = result["records"][0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(result["records"])

    def display_progress(self):
        """Display current progress dashboard"""
        os.system('clear' if os.name == 'posix' else 'cls')

        total = self.progress["total_pdfs"]
        processed = len([p for p in self.progress["pdfs"].values() if p["status"] == "completed"])
        pending = len([p for p in self.progress["pdfs"].values() if p["status"] == "pending"])
        failed = len([p for p in self.progress["pdfs"].values() if p["status"] == "failed"])
        manual = len([p for p in self.progress["pdfs"].values() if p["status"] == "manual_review"])

        print("=" * 50)
        print("Form 20 Extraction Progress")
        print("=" * 50)
        print(f"Total PDFs: {total}")
        print(f"Processed: {processed} ({processed/total*100:.1f}%)")
        print(f"Pending: {pending}")
        print(f"Failed: {failed}")
        print(f"Manual Review: {manual}")
        print()

        if self.progress["last_processed"]:
            last_pdf = self.progress["pdfs"][self.progress["last_processed"]]
            print(f"Last Completed: {self.progress['last_processed']}")
            print(f"  Records: {last_pdf.get('record_count', 'N/A')}")
            print(f"  Quality: {last_pdf.get('quality_score', 0):.2f}")

        # Estimate time remaining
        if processed > 0 and self.progress["start_time"]:
            elapsed = time.time() - self.progress["start_time"]
            rate = processed / elapsed
            remaining = pending / rate if rate > 0 else 0
            print(f"\nEstimated Time Remaining: {remaining/3600:.1f} hours")

        print("=" * 50)

    def run_extraction(self, start_from: Optional[str] = None, batch_mode: bool = True):
        """Main extraction loop"""
        logger.info("Starting Form 20 extraction process")

        if not self.progress["start_time"]:
            self.progress["start_time"] = time.time()

        # Resume from specific PDF or last checkpoint
        if start_from:
            current_pdf = start_from
        elif self.progress["last_processed"]:
            current_pdf = self.get_next_pending_pdf()
        else:
            current_pdf = self.get_next_pending_pdf()

        batch_count = 0

        while current_pdf:
            # Display progress
            self.display_progress()

            # Process PDF
            success, result = self.extract_pdf(current_pdf)

            if success:
                self.progress["last_processed"] = current_pdf

            # Save checkpoint
            batch_count += 1
            if batch_count >= self.config["checkpoint_interval"]:
                logger.info(f"Checkpoint: Saving progress after {batch_count} PDFs")
                self.save_progress()
                batch_count = 0

            # Get next PDF
            current_pdf = self.get_next_pending_pdf()

            # Small delay to prevent overload
            time.sleep(0.5)

        # Final save
        self.save_progress()
        logger.info("Extraction process completed")
        self.generate_final_report()

    def generate_final_report(self):
        """Generate comprehensive extraction report"""
        report_file = self.base_dir / "output/extraction_report.md"

        total = self.progress["total_pdfs"]
        completed = len([p for p in self.progress["pdfs"].values() if p["status"] == "completed"])
        failed = len([p for p in self.progress["pdfs"].values() if p["status"] == "failed"])
        manual = len([p for p in self.progress["pdfs"].values() if p["status"] == "manual_review"])

        total_records = sum(p.get("record_count", 0) for p in self.progress["pdfs"].values() if p["status"] == "completed")
        avg_quality = sum(p.get("quality_score", 0) for p in self.progress["pdfs"].values() if p["status"] == "completed") / max(completed, 1)

        report = f"""# Form 20 Extraction Report
Generated: {datetime.now().isoformat()}

## Summary
- Total PDFs: {total}
- Successfully Processed: {completed} ({completed/total*100:.1f}%)
- Failed: {failed}
- Pending Manual Review: {manual}
- Total Records Extracted: {total_records:,}
- Average Quality Score: {avg_quality:.2f}

## Failed PDFs
"""

        for ac, info in self.progress["pdfs"].items():
            if info["status"] == "failed":
                report += f"- {ac} ({info['district']}): {info.get('errors', ['Unknown error'])}\n"

        report += "\n## Manual Review Required\n"
        for ac, info in self.progress["pdfs"].items():
            if info["status"] == "manual_review":
                report += f"- {ac} ({info['district']}): Quality Score = {info.get('quality_score', 0):.2f}\n"

        with open(report_file, 'w') as f:
            f.write(report)

        logger.info(f"Final report generated: {report_file}")

def main():
    parser = argparse.ArgumentParser(description="Form 20 PDF Extraction System")
    parser.add_argument("--start", action="store_true", help="Start extraction process")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--from-pdf", help="Start from specific PDF (e.g., AC_216)")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--export-final", action="store_true", help="Export final consolidated CSV")

    args = parser.parse_args()

    extractor = Form20Extractor()

    if args.status:
        extractor.display_progress()
    elif args.start or args.resume:
        start_from = args.from_pdf if args.from_pdf else None
        extractor.run_extraction(start_from=start_from)
    elif args.export_final:
        logger.info("Exporting consolidated CSV...")
        # Implementation for consolidation
    else:
        parser.print_help()

if __name__ == "__main__":
    main()