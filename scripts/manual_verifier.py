#!/usr/bin/env python3
"""
Manual Verification Interface for Form 20 PDF Extraction
Allows users to verify, correct, and approve extracted data
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import argparse
import subprocess

class ManualVerifier:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.progress_file = self.base_dir / "tracking/extraction_progress.json"
        self.corrections_file = self.base_dir / "tracking/manual_corrections.json"
        self.output_dir = self.base_dir / "output/extracted_data"

    def load_progress(self) -> Dict:
        """Load progress tracking data"""
        if not self.progress_file.exists():
            print("Error: Progress file not found. Run extraction first.")
            sys.exit(1)

        with open(self.progress_file, 'r') as f:
            return json.load(f)

    def save_progress(self, progress: Dict):
        """Save updated progress"""
        with open(self.progress_file, 'w') as f:
            json.dump(progress, f, indent=2)

    def load_corrections(self) -> Dict:
        """Load manual corrections log"""
        if not self.corrections_file.exists():
            return {"corrections": [], "total_corrections": 0}

        with open(self.corrections_file, 'r') as f:
            return json.load(f)

    def save_corrections(self, corrections: Dict):
        """Save corrections log"""
        self.corrections_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.corrections_file, 'w') as f:
            json.dump(corrections, f, indent=2)

    def check_pdf(self, ac_number: str):
        """Check extraction results for a specific PDF"""
        progress = self.load_progress()

        if ac_number not in progress["pdfs"]:
            print(f"Error: {ac_number} not found in tracking.")
            return

        pdf_info = progress["pdfs"][ac_number]

        print("\n" + "=" * 60)
        print(f"EXTRACTION DETAILS: {ac_number}")
        print("=" * 60)
        print(f"District:         {pdf_info['district']}")
        print(f"File:             {pdf_info['file_path']}")
        print(f"Status:           {pdf_info['status']}")
        print(f"Tier:             {pdf_info.get('tier', 'N/A')}")
        print(f"Record Count:     {pdf_info.get('record_count', 'N/A')}")
        print(f"Quality Score:    {pdf_info.get('quality_score', 0):.2f}")
        print(f"Manual Verified:  {pdf_info.get('manual_verified', False)}")
        print(f"Retry Count:      {pdf_info.get('retry_count', 0)}")

        if pdf_info.get("errors"):
            print("\nErrors:")
            for error in pdf_info["errors"]:
                print(f"  - {error.get('error', error)[:100]}")

        # Show extracted data preview if available
        extracted_file = self.output_dir / f"{ac_number}_raw.json"
        if extracted_file.exists():
            with open(extracted_file, 'r') as f:
                data = json.load(f)

            if data.get("records"):
                print(f"\nExtracted Records: {len(data['records'])}")
                print("\nFirst 3 records preview:")
                for i, record in enumerate(data["records"][:3], 1):
                    print(f"\n  Record {i}:")
                    for key, value in list(record.items())[:5]:
                        print(f"    {key}: {value}")

        print("=" * 60)

    def verify_count(self, ac_number: str, expected_count: int):
        """Verify and update record count for a PDF"""
        progress = self.load_progress()

        if ac_number not in progress["pdfs"]:
            print(f"Error: {ac_number} not found in tracking.")
            return

        pdf_info = progress["pdfs"][ac_number]
        actual_count = pdf_info.get("record_count", 0)

        print(f"\nVerifying {ac_number}:")
        print(f"  Actual count:   {actual_count}")
        print(f"  Expected count: {expected_count}")

        if actual_count == expected_count:
            print("✓ Counts match!")
            pdf_info["manual_verified"] = True
            pdf_info["notes"] = f"Count verified: {expected_count}"
        else:
            print(f"✗ Count mismatch: {abs(actual_count - expected_count)} difference")

            response = input("Update count? (y/n): ").lower()
            if response == 'y':
                # Log correction
                corrections = self.load_corrections()
                corrections["corrections"].append({
                    "timestamp": datetime.now().isoformat(),
                    "ac_number": ac_number,
                    "field": "record_count",
                    "old_value": actual_count,
                    "new_value": expected_count,
                    "reason": "Manual count verification"
                })
                corrections["total_corrections"] += 1
                self.save_corrections(corrections)

                # Update progress
                pdf_info["record_count"] = expected_count
                pdf_info["manual_verified"] = True
                pdf_info["manual_corrections"].append({
                    "timestamp": datetime.now().isoformat(),
                    "field": "record_count",
                    "old": actual_count,
                    "new": expected_count
                })

                print(f"✓ Updated record count to {expected_count}")

        self.save_progress(progress)

    def review_flagged(self, limit: int = None):
        """Review all PDFs flagged for manual review"""
        progress = self.load_progress()

        flagged = [
            (ac, info) for ac, info in progress["pdfs"].items()
            if info["status"] == "manual_review"
        ]

        if not flagged:
            print("No PDFs flagged for manual review.")
            return

        print(f"\n{len(flagged)} PDFs need manual review:")
        print("-" * 60)

        count = 0
        for ac_number, pdf_info in flagged:
            if limit and count >= limit:
                break

            count += 1
            print(f"\n[{count}/{len(flagged)}] {ac_number} ({pdf_info['district']})")
            print(f"  Quality Score: {pdf_info.get('quality_score', 0):.2f}")
            print(f"  Record Count:  {pdf_info.get('record_count', 'N/A')}")

            # Show validation issues
            if pdf_info.get("validation_results"):
                issues = pdf_info["validation_results"].get("issues", [])
                if issues:
                    print("  Issues:")
                    for issue in issues[:3]:
                        print(f"    - {issue}")

            # Ask for action
            print("\n  Actions: [a]pprove, [r]eject, [c]orrect, [s]kip, [v]iew PDF, [q]uit")
            action = input("  Choose action: ").lower()

            if action == 'a':
                self.approve_pdf(ac_number)
            elif action == 'r':
                self.reject_pdf(ac_number)
            elif action == 'c':
                expected = input("  Enter correct record count: ")
                if expected.isdigit():
                    self.verify_count(ac_number, int(expected))
            elif action == 'v':
                self.open_pdf(ac_number)
            elif action == 'q':
                break
            elif action == 's':
                continue

    def approve_pdf(self, ac_number: str):
        """Approve a PDF extraction"""
        progress = self.load_progress()

        if ac_number not in progress["pdfs"]:
            print(f"Error: {ac_number} not found.")
            return

        pdf_info = progress["pdfs"][ac_number]
        pdf_info["status"] = "completed"
        pdf_info["manual_verified"] = True
        pdf_info["notes"] = f"Manually approved on {datetime.now().isoformat()}"

        self.save_progress(progress)
        print(f"✓ Approved {ac_number}")

    def reject_pdf(self, ac_number: str):
        """Reject a PDF extraction"""
        progress = self.load_progress()

        if ac_number not in progress["pdfs"]:
            print(f"Error: {ac_number} not found.")
            return

        reason = input("Rejection reason: ")

        pdf_info = progress["pdfs"][ac_number]
        pdf_info["status"] = "failed"
        pdf_info["manual_verified"] = True
        pdf_info["notes"] = f"Rejected: {reason}"
        pdf_info["errors"].append({
            "timestamp": datetime.now().isoformat(),
            "error": f"Manual rejection: {reason}"
        })

        self.save_progress(progress)
        print(f"✓ Rejected {ac_number}")

    def approve_batch(self, min_confidence: float = 0.95):
        """Approve all high-confidence extractions"""
        progress = self.load_progress()

        approved = 0
        for ac_number, pdf_info in progress["pdfs"].items():
            if (pdf_info["status"] == "manual_review" and
                pdf_info.get("quality_score", 0) >= min_confidence):

                pdf_info["status"] = "completed"
                pdf_info["manual_verified"] = True
                pdf_info["notes"] = f"Batch approved (Q>{min_confidence})"
                approved += 1

        self.save_progress(progress)
        print(f"✓ Batch approved {approved} PDFs with quality >= {min_confidence}")

    def open_pdf(self, ac_number: str):
        """Open PDF file for manual inspection"""
        progress = self.load_progress()

        if ac_number not in progress["pdfs"]:
            print(f"Error: {ac_number} not found.")
            return

        pdf_path = self.base_dir / progress["pdfs"][ac_number]["file_path"]

        if not pdf_path.exists():
            print(f"Error: PDF file not found at {pdf_path}")
            return

        # Try to open with system default PDF viewer
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", str(pdf_path)])
            elif sys.platform == "linux":  # Linux
                subprocess.run(["xdg-open", str(pdf_path)])
            elif sys.platform == "win32":  # Windows
                os.startfile(str(pdf_path))
            else:
                print(f"Please manually open: {pdf_path}")
        except Exception as e:
            print(f"Error opening PDF: {e}")
            print(f"Please manually open: {pdf_path}")

    def generate_verification_report(self):
        """Generate report of manual verifications"""
        progress = self.load_progress()
        corrections = self.load_corrections()

        verified = [
            (ac, info) for ac, info in progress["pdfs"].items()
            if info.get("manual_verified", False)
        ]

        report = f"""# Manual Verification Report
Generated: {datetime.now().isoformat()}

## Summary
- Total PDFs Manually Verified: {len(verified)}
- Total Corrections Made: {corrections.get('total_corrections', 0)}

## Verified PDFs
"""

        for ac_number, pdf_info in verified:
            report += f"\n### {ac_number} ({pdf_info['district']})\n"
            report += f"- Status: {pdf_info['status']}\n"
            report += f"- Quality Score: {pdf_info.get('quality_score', 0):.2f}\n"
            report += f"- Record Count: {pdf_info.get('record_count', 'N/A')}\n"
            if pdf_info.get("notes"):
                report += f"- Notes: {pdf_info['notes']}\n"

        if corrections.get("corrections"):
            report += "\n## Corrections Made\n"
            for correction in corrections["corrections"]:
                report += f"\n- **{correction['ac_number']}** ({correction['timestamp'][:10]})\n"
                report += f"  - Field: {correction['field']}\n"
                report += f"  - Changed from: {correction['old_value']} → {correction['new_value']}\n"
                report += f"  - Reason: {correction['reason']}\n"

        report_file = self.base_dir / "output/manual_verification_report.md"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        with open(report_file, 'w') as f:
            f.write(report)

        print(f"✓ Report generated: {report_file}")

    def interactive_mode(self):
        """Interactive verification mode"""
        print("\n" + "=" * 60)
        print("MANUAL VERIFICATION INTERFACE")
        print("=" * 60)

        while True:
            print("\nCommands:")
            print("  1. Check specific PDF")
            print("  2. Review flagged PDFs")
            print("  3. Verify record count")
            print("  4. Approve high-confidence batch")
            print("  5. Generate verification report")
            print("  6. Show statistics")
            print("  q. Quit")

            choice = input("\nEnter command: ").lower()

            if choice == '1':
                ac_number = input("Enter AC number (e.g., AC_216): ")
                self.check_pdf(ac_number)

            elif choice == '2':
                self.review_flagged()

            elif choice == '3':
                ac_number = input("Enter AC number: ")
                count = input("Enter expected count: ")
                if count.isdigit():
                    self.verify_count(ac_number, int(count))

            elif choice == '4':
                threshold = input("Enter minimum quality score (default 0.95): ")
                min_conf = float(threshold) if threshold else 0.95
                self.approve_batch(min_conf)

            elif choice == '5':
                self.generate_verification_report()

            elif choice == '6':
                self.show_statistics()

            elif choice == 'q':
                break

    def show_statistics(self):
        """Show verification statistics"""
        progress = self.load_progress()

        total = progress["total_pdfs"]
        verified = len([p for p in progress["pdfs"].values() if p.get("manual_verified", False)])
        completed = len([p for p in progress["pdfs"].values() if p["status"] == "completed"])
        review = len([p for p in progress["pdfs"].values() if p["status"] == "manual_review"])

        print("\n" + "-" * 40)
        print("VERIFICATION STATISTICS")
        print("-" * 40)
        print(f"Total PDFs:           {total}")
        print(f"Manually Verified:    {verified} ({verified/total*100:.1f}%)")
        print(f"Completed:            {completed}")
        print(f"Awaiting Review:      {review}")

        # Show quality distribution
        quality_scores = [p.get("quality_score", 0) for p in progress["pdfs"].values() if p.get("quality_score")]
        if quality_scores:
            print(f"\nQuality Scores:")
            print(f"  Average:  {sum(quality_scores)/len(quality_scores):.2f}")
            print(f"  Minimum:  {min(quality_scores):.2f}")
            print(f"  Maximum:  {max(quality_scores):.2f}")
            print(f"  >0.95:    {len([q for q in quality_scores if q > 0.95])}")
            print(f"  0.85-0.95: {len([q for q in quality_scores if 0.85 <= q <= 0.95])}")
            print(f"  <0.85:    {len([q for q in quality_scores if q < 0.85])}")

def main():
    parser = argparse.ArgumentParser(description="Manual Verification Interface")
    parser.add_argument("--check", help="Check specific PDF (e.g., AC_216)")
    parser.add_argument("--verify-count", help="Verify count (format: AC_216:307)")
    parser.add_argument("--review-flagged", action="store_true", help="Review flagged PDFs")
    parser.add_argument("--approve-batch", action="store_true", help="Approve high-confidence batch")
    parser.add_argument("--min-confidence", type=float, default=0.95, help="Minimum confidence for batch approval")
    parser.add_argument("--report", action="store_true", help="Generate verification report")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")

    args = parser.parse_args()
    verifier = ManualVerifier()

    if args.check:
        verifier.check_pdf(args.check)
    elif args.verify_count:
        parts = args.verify_count.split(":")
        if len(parts) == 2:
            ac_number, count = parts
            verifier.verify_count(ac_number, int(count))
        else:
            print("Format: AC_NUMBER:EXPECTED_COUNT (e.g., AC_216:307)")
    elif args.review_flagged:
        verifier.review_flagged()
    elif args.approve_batch:
        verifier.approve_batch(args.min_confidence)
    elif args.report:
        verifier.generate_verification_report()
    elif args.interactive:
        verifier.interactive_mode()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()