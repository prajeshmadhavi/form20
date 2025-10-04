#!/usr/bin/env python3
"""
Progress Manager for Form 20 PDF Extraction
Handles initialization, tracking, and reporting of extraction progress
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import argparse

class ProgressManager:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.progress_file = self.base_dir / "tracking/extraction_progress.json"
        self.classification_file = self.base_dir / "tracking/pdf_classification.json"
        self.quality_metrics_file = self.base_dir / "tracking/quality_metrics.json"
        self.error_log_file = self.base_dir / "tracking/error_log.json"

    def initialize_tracking(self, force: bool = False):
        """Initialize all tracking files"""
        if self.progress_file.exists() and not force:
            print(f"Progress file already exists. Use --force to reinitialize.")
            return

        # Create tracking directory
        tracking_dir = self.base_dir / "tracking"
        tracking_dir.mkdir(parents=True, exist_ok=True)

        # Initialize extraction progress
        progress = self.create_progress_structure()
        with open(self.progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
        print(f"✓ Created progress tracking: {self.progress_file}")

        # Initialize quality metrics
        quality_metrics = {
            "overall_quality_score": 0.0,
            "pdfs_processed": 0,
            "total_records_extracted": 0,
            "average_records_per_pdf": 0,
            "field_completeness": {},
            "validation_failures": [],
            "manual_corrections_made": 0,
            "last_updated": datetime.now().isoformat()
        }
        with open(self.quality_metrics_file, 'w') as f:
            json.dump(quality_metrics, f, indent=2)
        print(f"✓ Created quality metrics: {self.quality_metrics_file}")

        # Initialize error log
        error_log = {
            "total_errors": 0,
            "errors_by_type": {},
            "errors": [],
            "last_updated": datetime.now().isoformat()
        }
        with open(self.error_log_file, 'w') as f:
            json.dump(error_log, f, indent=2)
        print(f"✓ Created error log: {self.error_log_file}")

    def create_progress_structure(self) -> Dict:
        """Create the initial progress tracking structure"""
        vidhansabha_dir = self.base_dir / "VIDHANSABHA_2024"

        if not vidhansabha_dir.exists():
            raise FileNotFoundError(f"VIDHANSABHA_2024 directory not found at {vidhansabha_dir}")

        progress = {
            "total_pdfs": 0,
            "processed": 0,
            "pending": 0,
            "failed": 0,
            "manual_review": 0,
            "last_processed": None,
            "start_time": None,
            "end_time": None,
            "checkpoints": [],
            "pdfs": {},
            "statistics": {
                "by_district": {},
                "by_tier": {"tier_1": 0, "tier_2": 0, "tier_3": 0},
                "total_records": 0,
                "average_quality": 0.0
            }
        }

        pdf_count = 0
        district_stats = {}

        # Scan all PDFs
        for district_dir in sorted(vidhansabha_dir.iterdir()):
            if district_dir.is_dir():
                district_name = district_dir.name
                district_pdf_count = 0

                for pdf_file in sorted(district_dir.glob("*.pdf")):
                    ac_number = pdf_file.stem
                    pdf_count += 1
                    district_pdf_count += 1

                    progress["pdfs"][ac_number] = {
                        "id": pdf_count,
                        "district": district_name,
                        "file_path": str(pdf_file.relative_to(self.base_dir)),
                        "file_size": pdf_file.stat().st_size,
                        "tier": None,
                        "status": "pending",
                        "extraction_timestamp": None,
                        "processing_time": None,
                        "record_count": None,
                        "quality_score": None,
                        "confidence_score": None,
                        "manual_verified": False,
                        "manual_corrections": [],
                        "validation_results": {},
                        "errors": [],
                        "retry_count": 0,
                        "notes": ""
                    }

                district_stats[district_name] = {
                    "total": district_pdf_count,
                    "processed": 0,
                    "failed": 0
                }

        progress["total_pdfs"] = pdf_count
        progress["pending"] = pdf_count
        progress["statistics"]["by_district"] = district_stats

        return progress

    def get_status(self, detailed: bool = False):
        """Get current extraction status"""
        if not self.progress_file.exists():
            print("No progress file found. Run --init first.")
            return

        with open(self.progress_file, 'r') as f:
            progress = json.load(f)

        # Calculate statistics
        total = progress["total_pdfs"]
        completed = len([p for p in progress["pdfs"].values() if p["status"] == "completed"])
        pending = len([p for p in progress["pdfs"].values() if p["status"] == "pending"])
        failed = len([p for p in progress["pdfs"].values() if p["status"] == "failed"])
        manual = len([p for p in progress["pdfs"].values() if p["status"] == "manual_review"])
        in_progress = len([p for p in progress["pdfs"].values() if p["status"] == "in_progress"])

        print("\n" + "=" * 60)
        print("FORM 20 EXTRACTION STATUS")
        print("=" * 60)
        print(f"Total PDFs:       {total:>4}")
        print(f"Completed:        {completed:>4} ({completed/total*100:>5.1f}%)")
        print(f"In Progress:      {in_progress:>4}")
        print(f"Pending:          {pending:>4}")
        print(f"Failed:           {failed:>4}")
        print(f"Manual Review:    {manual:>4}")

        if progress.get("start_time"):
            print(f"\nStarted: {progress['start_time']}")
            if progress.get("end_time"):
                print(f"Completed: {progress['end_time']}")

        if progress.get("last_processed"):
            last_pdf = progress["pdfs"][progress["last_processed"]]
            print(f"\nLast Processed: {progress['last_processed']}")
            print(f"  District: {last_pdf['district']}")
            print(f"  Records: {last_pdf.get('record_count', 'N/A')}")
            print(f"  Quality: {last_pdf.get('quality_score', 0):.2f}")

        # District breakdown
        if detailed:
            print("\n" + "-" * 60)
            print("DISTRICT BREAKDOWN")
            print("-" * 60)

            districts = {}
            for ac, info in progress["pdfs"].items():
                district = info["district"]
                if district not in districts:
                    districts[district] = {"total": 0, "completed": 0, "failed": 0}
                districts[district]["total"] += 1
                if info["status"] == "completed":
                    districts[district]["completed"] += 1
                elif info["status"] == "failed":
                    districts[district]["failed"] += 1

            for district in sorted(districts.keys()):
                stats = districts[district]
                completion = stats["completed"] / stats["total"] * 100 if stats["total"] > 0 else 0
                print(f"{district:30} {stats['completed']:>3}/{stats['total']:<3} ({completion:>5.1f}%)")

            # Show failures
            if failed > 0:
                print("\n" + "-" * 60)
                print("FAILED PDFS")
                print("-" * 60)
                for ac, info in progress["pdfs"].items():
                    if info["status"] == "failed":
                        errors = info.get("errors", [])
                        last_error = errors[-1] if errors else {"error": "Unknown error"}
                        print(f"{ac:10} ({info['district']:20}) - {last_error.get('error', 'Unknown')[:50]}")

        print("=" * 60 + "\n")

    def reset_pdf(self, ac_number: str):
        """Reset a specific PDF to pending status"""
        if not self.progress_file.exists():
            print("No progress file found.")
            return

        with open(self.progress_file, 'r') as f:
            progress = json.load(f)

        if ac_number not in progress["pdfs"]:
            print(f"PDF {ac_number} not found in tracking.")
            return

        # Reset the PDF
        pdf_info = progress["pdfs"][ac_number]
        pdf_info["status"] = "pending"
        pdf_info["retry_count"] = 0
        pdf_info["errors"] = []
        pdf_info["extraction_timestamp"] = None
        pdf_info["record_count"] = None
        pdf_info["quality_score"] = None

        # Update counts
        progress["pending"] = len([p for p in progress["pdfs"].values() if p["status"] == "pending"])
        progress["processed"] = len([p for p in progress["pdfs"].values() if p["status"] == "completed"])

        with open(self.progress_file, 'w') as f:
            json.dump(progress, f, indent=2)

        print(f"✓ Reset {ac_number} to pending status")

    def mark_complete(self, ac_number: str, record_count: int, quality_score: float):
        """Manually mark a PDF as complete"""
        if not self.progress_file.exists():
            print("No progress file found.")
            return

        with open(self.progress_file, 'r') as f:
            progress = json.load(f)

        if ac_number not in progress["pdfs"]:
            print(f"PDF {ac_number} not found in tracking.")
            return

        pdf_info = progress["pdfs"][ac_number]
        pdf_info["status"] = "completed"
        pdf_info["record_count"] = record_count
        pdf_info["quality_score"] = quality_score
        pdf_info["extraction_timestamp"] = datetime.now().isoformat()
        pdf_info["manual_verified"] = True

        # Update counts
        progress["processed"] = len([p for p in progress["pdfs"].values() if p["status"] == "completed"])
        progress["pending"] = len([p for p in progress["pdfs"].values() if p["status"] == "pending"])

        with open(self.progress_file, 'w') as f:
            json.dump(progress, f, indent=2)

        print(f"✓ Marked {ac_number} as complete with {record_count} records (Q: {quality_score:.2f})")

    def create_checkpoint(self, name: str = None):
        """Create a checkpoint of current progress"""
        if not self.progress_file.exists():
            print("No progress file found.")
            return

        with open(self.progress_file, 'r') as f:
            progress = json.load(f)

        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "name": name or f"checkpoint_{len(progress.get('checkpoints', [])) + 1}",
            "processed": len([p for p in progress["pdfs"].values() if p["status"] == "completed"]),
            "failed": len([p for p in progress["pdfs"].values() if p["status"] == "failed"]),
            "pending": len([p for p in progress["pdfs"].values() if p["status"] == "pending"])
        }

        if "checkpoints" not in progress:
            progress["checkpoints"] = []

        progress["checkpoints"].append(checkpoint)

        with open(self.progress_file, 'w') as f:
            json.dump(progress, f, indent=2)

        # Create backup
        backup_dir = self.base_dir / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup_file = backup_dir / f"progress_{checkpoint['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_file, 'w') as f:
            json.dump(progress, f, indent=2)

        print(f"✓ Created checkpoint: {checkpoint['name']}")
        print(f"✓ Backup saved to: {backup_file}")

    def get_next_batch(self, batch_size: int = 10) -> List[str]:
        """Get next batch of PDFs to process"""
        if not self.progress_file.exists():
            return []

        with open(self.progress_file, 'r') as f:
            progress = json.load(f)

        batch = []
        for ac_number, info in progress["pdfs"].items():
            if info["status"] == "pending" and len(batch) < batch_size:
                batch.append(ac_number)

        return batch

def main():
    parser = argparse.ArgumentParser(description="Progress Manager for Form 20 Extraction")
    parser.add_argument("--init", action="store_true", help="Initialize tracking files")
    parser.add_argument("--force", action="store_true", help="Force reinitialize even if files exist")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--detailed", action="store_true", help="Show detailed status")
    parser.add_argument("--reset", help="Reset specific PDF to pending (e.g., AC_216)")
    parser.add_argument("--mark-complete", help="Mark PDF as complete (format: AC_216:307:0.95)")
    parser.add_argument("--checkpoint", help="Create a checkpoint with optional name")
    parser.add_argument("--next-batch", type=int, help="Get next batch of PDFs to process")

    args = parser.parse_args()
    manager = ProgressManager()

    if args.init:
        manager.initialize_tracking(force=args.force)
    elif args.status or args.detailed:
        manager.get_status(detailed=args.detailed)
    elif args.reset:
        manager.reset_pdf(args.reset)
    elif args.mark_complete:
        parts = args.mark_complete.split(":")
        if len(parts) == 3:
            ac_number, record_count, quality = parts
            manager.mark_complete(ac_number, int(record_count), float(quality))
        else:
            print("Format: AC_NUMBER:RECORD_COUNT:QUALITY_SCORE (e.g., AC_216:307:0.95)")
    elif args.checkpoint:
        manager.create_checkpoint(args.checkpoint)
    elif args.next_batch:
        batch = manager.get_next_batch(args.next_batch)
        print(f"Next batch ({len(batch)} PDFs): {', '.join(batch)}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()