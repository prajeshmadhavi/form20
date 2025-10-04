#!/usr/bin/env python3
"""
Quality Checker for Type 3 PDF Extraction Results
Analyzes all JSON outputs and identifies PDFs requiring re-processing
"""

import json
import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

class QualityChecker:
    def __init__(self):
        self.parsed_data_dir = Path("parsedData")
        self.quality_report_file = Path("quality_assessment_report.json")
        self.reprocess_queue_file = Path("reprocess_queue.json")

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('quality_check.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def assess_json_quality(self, json_file: Path) -> Dict:
        """Assess the quality of a single JSON extraction"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            assessment = {
                "file_name": json_file.name,
                "ac_number": data.get("Constituency Number"),
                "constituency_name": data.get("constituency_name", ""),
                "total_electors": data.get("Total Number of Electors"),
                "quality_score": 0,
                "issues": [],
                "completeness": {},
                "needs_reprocessing": False
            }

            # Check basic constituency info
            if assessment["ac_number"]:
                assessment["quality_score"] += 10
                assessment["completeness"]["constituency_number"] = True
            else:
                assessment["issues"].append("Missing constituency number")
                assessment["completeness"]["constituency_number"] = False

            if assessment["total_electors"]:
                assessment["quality_score"] += 10
                assessment["completeness"]["total_electors"] = True
            else:
                assessment["issues"].append("Missing total electors")
                assessment["completeness"]["total_electors"] = False

            # Check polling station details
            serial_details = data.get("serial_no_wise_details", [])
            if serial_details and len(serial_details) > 0:
                assessment["quality_score"] += 30
                assessment["completeness"]["polling_stations"] = True
                assessment["completeness"]["polling_station_count"] = len(serial_details)

                # Check if polling stations have candidate votes
                stations_with_votes = sum(1 for station in serial_details
                                        if station.get("candidate_votes") and len(station.get("candidate_votes", [])) > 0)

                if stations_with_votes > 0:
                    assessment["quality_score"] += 20
                    assessment["completeness"]["candidate_votes_per_station"] = True
                else:
                    assessment["issues"].append("Polling stations missing candidate votes")
                    assessment["completeness"]["candidate_votes_per_station"] = False
            else:
                assessment["issues"].append("No polling station details extracted")
                assessment["completeness"]["polling_stations"] = False
                assessment["completeness"]["polling_station_count"] = 0

            # Check candidates list
            candidates = data.get("candidates", [])
            if candidates and len(candidates) > 0:
                assessment["quality_score"] += 20
                assessment["completeness"]["candidates_list"] = True
                assessment["completeness"]["candidate_count"] = len(candidates)
            else:
                assessment["issues"].append("No candidates list extracted")
                assessment["completeness"]["candidates_list"] = False
                assessment["completeness"]["candidate_count"] = 0

            # Check elected person
            elected_person = data.get("Elected Person Name")
            if elected_person:
                assessment["quality_score"] += 10
                assessment["completeness"]["elected_person"] = True
            else:
                assessment["issues"].append("No elected person identified")
                assessment["completeness"]["elected_person"] = False

            # Determine if reprocessing is needed
            # Criteria: Quality score < 50 OR no polling stations OR no candidates
            if (assessment["quality_score"] < 50 or
                not assessment["completeness"]["polling_stations"] or
                not assessment["completeness"]["candidates_list"]):
                assessment["needs_reprocessing"] = True

            # Quality categorization
            if assessment["quality_score"] >= 80:
                assessment["quality_category"] = "Excellent"
            elif assessment["quality_score"] >= 60:
                assessment["quality_category"] = "Good"
            elif assessment["quality_score"] >= 40:
                assessment["quality_category"] = "Fair"
            else:
                assessment["quality_category"] = "Poor"

            return assessment

        except Exception as e:
            self.logger.error(f"Error assessing {json_file}: {e}")
            return {
                "file_name": json_file.name,
                "ac_number": None,
                "quality_score": 0,
                "issues": [f"File read error: {str(e)}"],
                "needs_reprocessing": True,
                "quality_category": "Error"
            }

    def get_all_json_files(self) -> List[Path]:
        """Get all AC JSON files from parsedData directory"""
        json_files = []

        # Look for all AC_*.json files (including VISION and COMPLETE_VISION)
        for pattern in ["AC_*.json", "AC_*_VISION.json", "AC_*_COMPLETE_VISION.json"]:
            json_files.extend(list(self.parsed_data_dir.glob(pattern)))

        # Remove backup files
        json_files = [f for f in json_files if "backup" not in f.name]

        # For each AC number, keep only the best version (prefer COMPLETE_VISION > VISION > regular)
        ac_files = {}
        for json_file in json_files:
            # Extract AC number from filename
            ac_match = json_file.name.replace("AC_", "").split("_")[0].split(".")[0]
            try:
                ac_num = int(ac_match)

                if ac_num not in ac_files:
                    ac_files[ac_num] = json_file
                else:
                    # Prefer COMPLETE_VISION > VISION > regular
                    current_file = ac_files[ac_num]
                    if "COMPLETE_VISION" in json_file.name:
                        ac_files[ac_num] = json_file
                    elif "VISION" in json_file.name and "COMPLETE_VISION" not in current_file.name:
                        ac_files[ac_num] = json_file
            except ValueError:
                continue

        return sorted(ac_files.values(), key=lambda x: int(x.name.replace("AC_", "").split("_")[0].split(".")[0]))

    def run_quality_assessment(self):
        """Run quality assessment on all JSON files"""
        self.logger.info("🔍 Starting comprehensive quality assessment...")

        json_files = self.get_all_json_files()
        self.logger.info(f"📋 Found {len(json_files)} JSON files to assess")

        quality_report = {
            "assessment_timestamp": datetime.now().isoformat(),
            "total_files_assessed": len(json_files),
            "summary": {
                "excellent": 0,
                "good": 0,
                "fair": 0,
                "poor": 0,
                "errors": 0,
                "needs_reprocessing": 0
            },
            "detailed_assessments": []
        }

        reprocess_queue = {
            "created_timestamp": datetime.now().isoformat(),
            "total_files_to_reprocess": 0,
            "reprocess_list": []
        }

        for i, json_file in enumerate(json_files, 1):
            self.logger.info(f"📊 Assessing {i}/{len(json_files)}: {json_file.name}")

            assessment = self.assess_json_quality(json_file)
            quality_report["detailed_assessments"].append(assessment)

            # Update summary counts
            category = assessment.get("quality_category", "Error").lower()
            if category in quality_report["summary"]:
                quality_report["summary"][category] += 1
            else:
                quality_report["summary"]["errors"] += 1

            if assessment["needs_reprocessing"]:
                quality_report["summary"]["needs_reprocessing"] += 1
                reprocess_queue["reprocess_list"].append({
                    "ac_number": assessment["ac_number"],
                    "file_name": assessment["file_name"],
                    "quality_score": assessment["quality_score"],
                    "issues": assessment["issues"],
                    "priority": "high" if assessment["quality_score"] < 30 else "medium"
                })

        reprocess_queue["total_files_to_reprocess"] = len(reprocess_queue["reprocess_list"])

        # Save reports
        with open(self.quality_report_file, 'w', encoding='utf-8') as f:
            json.dump(quality_report, f, indent=2, ensure_ascii=False)

        with open(self.reprocess_queue_file, 'w', encoding='utf-8') as f:
            json.dump(reprocess_queue, f, indent=2, ensure_ascii=False)

        # Print summary
        self.logger.info("📊 QUALITY ASSESSMENT COMPLETED!")
        self.logger.info(f"   Total files assessed: {quality_report['total_files_assessed']}")
        self.logger.info(f"   Excellent quality: {quality_report['summary']['excellent']}")
        self.logger.info(f"   Good quality: {quality_report['summary']['good']}")
        self.logger.info(f"   Fair quality: {quality_report['summary']['fair']}")
        self.logger.info(f"   Poor quality: {quality_report['summary']['poor']}")
        self.logger.info(f"   Errors: {quality_report['summary']['errors']}")
        self.logger.info(f"   📋 Files needing reprocessing: {quality_report['summary']['needs_reprocessing']}")

        return quality_report, reprocess_queue

    def show_quality_summary(self):
        """Display quality assessment summary"""
        if not self.quality_report_file.exists():
            print("❌ No quality assessment found. Run --assess first.")
            return

        with open(self.quality_report_file, 'r') as f:
            report = json.load(f)

        print("\n" + "="*60)
        print("📊 EXTRACTION QUALITY ASSESSMENT SUMMARY")
        print("="*60)
        print(f"Assessment Date: {report['assessment_timestamp']}")
        print(f"Total Files: {report['total_files_assessed']}")
        print()
        print("Quality Distribution:")
        print(f"  🟢 Excellent (80-100): {report['summary']['excellent']}")
        print(f"  🟡 Good (60-79): {report['summary']['good']}")
        print(f"  🟠 Fair (40-59): {report['summary']['fair']}")
        print(f"  🔴 Poor (0-39): {report['summary']['poor']}")
        print(f"  ❌ Errors: {report['summary']['errors']}")
        print()
        print(f"📋 Files Needing Reprocessing: {report['summary']['needs_reprocessing']}")

        if report['summary']['needs_reprocessing'] > 0:
            print("\nSample files needing reprocessing:")
            poor_files = [a for a in report['detailed_assessments']
                         if a['needs_reprocessing']][:5]
            for file_info in poor_files:
                print(f"  • {file_info['file_name']} (Score: {file_info['quality_score']}/100)")
                print(f"    Issues: {', '.join(file_info['issues'][:2])}")

        print("="*60)

def main():
    checker = QualityChecker()

    if len(sys.argv) > 1:
        if sys.argv[1] == "--assess":
            checker.run_quality_assessment()
        elif sys.argv[1] == "--summary":
            checker.show_quality_summary()
        elif sys.argv[1] == "--help":
            print("Usage:")
            print("  python quality_checker.py --assess   # Run quality assessment")
            print("  python quality_checker.py --summary  # Show assessment summary")
            print("  python quality_checker.py --help     # Show this help")
        else:
            print("Invalid argument. Use --help for usage information.")
    else:
        checker.show_quality_summary()

if __name__ == "__main__":
    main()