#!/usr/bin/env python3
"""
Vision Quality Assessor - New Strategy Implementation
Assesses all generated JSON files and marks low-quality ones as pending
Strategy: Use only claude_vision_extractor.py, abandon OCR completely
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

class VisionQualityAssessor:
    def __init__(self):
        self.tracking_file = Path("tracking.json")
        self.parsed_data_dir = Path("parsedData")
        self.min_file_size = 600  # bytes

        # Quality thresholds
        self.quality_criteria = {
            "min_total_electors": True,
            "min_candidates": 2,
            "min_polling_stations": 1,
            "elected_person_required": True
        }

    def load_tracking_data(self) -> Dict:
        """Load current tracking data"""
        if not self.tracking_file.exists():
            print("❌ tracking.json not found")
            return {}

        with open(self.tracking_file, 'r') as f:
            return json.load(f)

    def assess_file_size(self, json_file: Path) -> Tuple[bool, int]:
        """Check if file size meets minimum requirement"""
        if not json_file.exists():
            return False, 0

        file_size = json_file.stat().st_size
        return file_size >= self.min_file_size, file_size

    def assess_data_quality(self, json_file: Path) -> Tuple[bool, Dict]:
        """Assess the quality of extracted data"""
        if not json_file.exists():
            return False, {"error": "File not found"}

        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
        except:
            return False, {"error": "Invalid JSON"}

        quality_issues = []
        quality_score = 0

        # Check constituency number (10 points)
        if data.get("Constituency Number"):
            quality_score += 10
        else:
            quality_issues.append("Missing constituency number")

        # Check total electors (15 points)
        total_electors = data.get("Total Number of Electors")
        if total_electors and isinstance(total_electors, int) and total_electors > 0:
            quality_score += 15
        else:
            quality_issues.append("Missing or invalid total electors")

        # Check polling station details (25 points)
        polling_stations = data.get("serial_no_wise_details", [])
        if polling_stations and len(polling_stations) >= 1:
            quality_score += 25
            # Additional points for comprehensive polling data
            if len(polling_stations) >= 10:
                quality_score += 5
        else:
            quality_issues.append("No polling station details")

        # Check candidates list (25 points)
        candidates = data.get("candidates", [])
        if candidates and len(candidates) >= 2:
            quality_score += 25
            # Additional points for detailed candidate info
            if len(candidates) >= 5:
                quality_score += 5
        else:
            quality_issues.append("Insufficient candidates data")

        # Check elected person (15 points)
        elected_person = data.get("Elected Person Name")
        if elected_person and elected_person.strip():
            quality_score += 15
        else:
            quality_issues.append("Missing elected person")

        # Check for extraction method (bonus points)
        extraction_method = data.get("extraction_method", "")
        if "vision" in extraction_method.lower():
            quality_score += 5

        quality_passed = quality_score >= 60  # 60% threshold

        assessment = {
            "quality_score": quality_score,
            "quality_passed": quality_passed,
            "issues": quality_issues,
            "extraction_method": extraction_method,
            "candidates_count": len(candidates),
            "polling_stations_count": len(polling_stations),
            "has_elected_person": bool(elected_person and elected_person.strip())
        }

        return quality_passed, assessment

    def assess_all_json_files(self) -> Dict:
        """Assess all JSON files in parsedData directory"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "total_files": 0,
            "size_failures": 0,
            "quality_failures": 0,
            "pending_files": [],
            "good_files": [],
            "assessment_details": {}
        }

        if not self.parsed_data_dir.exists():
            print("❌ parsedData directory not found")
            return results

        json_files = list(self.parsed_data_dir.glob("AC_*.json"))

        # Filter out backup files
        json_files = [f for f in json_files if "_backup_" not in f.name]

        results["total_files"] = len(json_files)

        print(f"🔍 Assessing {len(json_files)} JSON files...")

        for json_file in sorted(json_files):
            ac_number_str = json_file.stem.replace("AC_", "")

            # Skip backup files and invalid AC numbers
            if "_backup_" in ac_number_str or not ac_number_str.isdigit():
                continue

            ac_number = ac_number_str

            # Check file size
            size_ok, file_size = self.assess_file_size(json_file)

            # Check data quality
            quality_ok, quality_assessment = self.assess_data_quality(json_file)

            file_assessment = {
                "file_size": file_size,
                "size_ok": size_ok,
                "quality_ok": quality_ok,
                "quality_details": quality_assessment
            }

            results["assessment_details"][ac_number] = file_assessment

            # Determine if file needs reprocessing
            needs_reprocessing = not size_ok or not quality_ok

            if needs_reprocessing:
                reason = []
                if not size_ok:
                    reason.append(f"file size {file_size} < {self.min_file_size} bytes")
                    results["size_failures"] += 1
                if not quality_ok:
                    reason.append(f"quality score {quality_assessment.get('quality_score', 0)}/100")
                    results["quality_failures"] += 1

                results["pending_files"].append({
                    "ac_number": int(ac_number),
                    "file_name": json_file.name,
                    "reason": ", ".join(reason),
                    "file_size": file_size,
                    "quality_score": quality_assessment.get("quality_score", 0)
                })

                print(f"❌ AC_{ac_number}: PENDING - {', '.join(reason)}")
            else:
                results["good_files"].append({
                    "ac_number": int(ac_number),
                    "file_name": json_file.name,
                    "file_size": file_size,
                    "quality_score": quality_assessment.get("quality_score", 0)
                })

                print(f"✅ AC_{ac_number}: GOOD - {file_size} bytes, quality {quality_assessment.get('quality_score', 0)}/100")

        return results

    def update_tracking_json(self, assessment_results: Dict) -> bool:
        """Update tracking.json with new pending statuses"""
        tracking_data = self.load_tracking_data()

        if not tracking_data:
            return False

        # Create lookup for pending files
        pending_ac_numbers = {item["ac_number"] for item in assessment_results["pending_files"]}

        # Update PDF statuses
        updated_count = 0
        for pdf_record in tracking_data.get("pdfs", []):
            ac_number = pdf_record.get("ac_number")

            if ac_number in pending_ac_numbers:
                # Find the specific assessment
                pending_info = next((p for p in assessment_results["pending_files"] if p["ac_number"] == ac_number), None)

                old_status = pdf_record.get("status", "unknown")
                pdf_record["status"] = "pending"
                pdf_record["vision_assessment"] = {
                    "needs_reprocessing": True,
                    "reason": pending_info["reason"] if pending_info else "quality issues",
                    "file_size": pending_info["file_size"] if pending_info else 0,
                    "quality_score": pending_info["quality_score"] if pending_info else 0,
                    "assessment_timestamp": datetime.now().isoformat(),
                    "previous_status": old_status
                }

                updated_count += 1
                print(f"📝 Updated AC_{ac_number}: {old_status} → pending")
            else:
                # Mark as completed if it was pending and now good
                if pdf_record.get("status") == "pending":
                    good_info = next((g for g in assessment_results["good_files"] if g["ac_number"] == ac_number), None)
                    if good_info:
                        pdf_record["status"] = "completed"
                        pdf_record["vision_assessment"] = {
                            "needs_reprocessing": False,
                            "file_size": good_info["file_size"],
                            "quality_score": good_info["quality_score"],
                            "assessment_timestamp": datetime.now().isoformat()
                        }
                        updated_count += 1
                        print(f"📝 Updated AC_{ac_number}: pending → completed")

        # Update summary statistics
        tracking_data["last_vision_assessment"] = {
            "timestamp": datetime.now().isoformat(),
            "total_assessed": assessment_results["total_files"],
            "pending_count": len(assessment_results["pending_files"]),
            "good_count": len(assessment_results["good_files"]),
            "size_failures": assessment_results["size_failures"],
            "quality_failures": assessment_results["quality_failures"],
            "records_updated": updated_count
        }

        # Save updated tracking data
        with open(self.tracking_file, 'w') as f:
            json.dump(tracking_data, f, indent=2, ensure_ascii=False)

        print(f"💾 Updated tracking.json - {updated_count} records modified")
        return True

    def create_reprocessing_queue(self, assessment_results: Dict) -> bool:
        """Create queue for vision-only reprocessing"""
        queue_file = Path("vision_reprocess_queue.json")

        queue_data = {
            "created_timestamp": datetime.now().isoformat(),
            "strategy": "vision_only",
            "total_files_to_reprocess": len(assessment_results["pending_files"]),
            "reprocess_list": []
        }

        for pending_file in assessment_results["pending_files"]:
            queue_data["reprocess_list"].append({
                "ac_number": pending_file["ac_number"],
                "file_name": pending_file["file_name"],
                "reason": pending_file["reason"],
                "file_size": pending_file["file_size"],
                "quality_score": pending_file["quality_score"],
                "priority": "high" if pending_file["file_size"] < 100 else "medium"
            })

        # Sort by priority and quality score
        queue_data["reprocess_list"].sort(key=lambda x: (x["priority"] != "high", x["quality_score"]))

        with open(queue_file, 'w') as f:
            json.dump(queue_data, f, indent=2, ensure_ascii=False)

        print(f"📋 Created vision reprocess queue: {len(queue_data['reprocess_list'])} files")
        return True

    def run_assessment(self):
        """Run complete assessment and update tracking"""
        print("🚀 Starting Vision Quality Assessment")
        print("📋 Strategy: Vision LLM only, abandon OCR completely")
        print(f"📏 Minimum file size: {self.min_file_size} bytes")
        print("🎯 Quality threshold: 60/100")
        print()

        # Assess all files
        assessment_results = self.assess_all_json_files()

        # Print summary
        print("\n" + "="*60)
        print("📊 ASSESSMENT SUMMARY")
        print("="*60)
        print(f"Total files assessed: {assessment_results['total_files']}")
        print(f"Good quality files: {len(assessment_results['good_files'])}")
        print(f"Files needing reprocessing: {len(assessment_results['pending_files'])}")
        print(f"  - Size failures: {assessment_results['size_failures']}")
        print(f"  - Quality failures: {assessment_results['quality_failures']}")

        if assessment_results["pending_files"]:
            print(f"\n📋 Files marked as PENDING for vision reprocessing:")
            for pending in assessment_results["pending_files"]:
                print(f"  AC_{pending['ac_number']}: {pending['reason']}")

        # Update tracking.json
        print("\n📝 Updating tracking.json...")
        self.update_tracking_json(assessment_results)

        # Create reprocessing queue
        print("📋 Creating vision reprocessing queue...")
        self.create_reprocessing_queue(assessment_results)

        # Save detailed assessment
        assessment_file = Path("vision_assessment_report.json")
        with open(assessment_file, 'w') as f:
            json.dump(assessment_results, f, indent=2, ensure_ascii=False)

        print(f"💾 Detailed assessment saved to: {assessment_file}")
        print("\n✅ Vision quality assessment completed!")

        return assessment_results

def main():
    assessor = VisionQualityAssessor()

    if len(sys.argv) > 1:
        if sys.argv[1] == "--run":
            assessor.run_assessment()
        elif sys.argv[1] == "--help":
            print("Usage:")
            print("  python vision_quality_assessor.py --run   # Run complete assessment")
            print("  python vision_quality_assessor.py --help # Show this help")
        else:
            print("Invalid argument. Use --help for usage information.")
    else:
        print("Use --run to start assessment or --help for usage.")

if __name__ == "__main__":
    main()