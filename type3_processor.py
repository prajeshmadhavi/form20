#!/usr/bin/env python3
"""
Type 3 Processor - Vision-Only Strategy
Uses ONLY claude_vision_extractor.py for all Type 3 PDF processing
Consolidated single processor for Type 3 files
"""

import json
import os
import sys
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List

class Type3Processor:
    def __init__(self):
        self.reprocess_queue_file = Path("vision_reprocess_queue.json")
        self.reprocess_progress_file = Path("vision_reprocess_progress.json")

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('type3_processing.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def load_reprocess_queue(self) -> List[Dict]:
        """Load the list of files needing vision reprocessing"""
        if not self.reprocess_queue_file.exists():
            self.logger.error("No reprocess queue found. Run vision_quality_assessor.py --run first.")
            return []

        with open(self.reprocess_queue_file, 'r') as f:
            data = json.load(f)

        return data.get("reprocess_list", [])

    def vision_extract_only(self, ac_number: int) -> bool:
        """Use ONLY Claude Vision extraction - no OCR fallback"""
        try:
            self.logger.info(f"🤖 Vision-only extraction for AC_{ac_number}")

            # Remove existing output to force fresh processing
            output_file = Path(f"parsedData/AC_{ac_number}.json")
            if output_file.exists():
                backup_file = Path(f"parsedData/AC_{ac_number}_pre_vision_{int(time.time())}.json")
                output_file.rename(backup_file)
                self.logger.info(f"📦 Backed up existing file to {backup_file.name}")

            # Run Claude Vision extraction
            cmd = [sys.executable, "claude_vision_extractor.py", str(ac_number)]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=900  # 15 minutes timeout
            )

            if result.returncode == 0:
                # Check if the output has meaningful data
                if output_file.exists():
                    file_size = output_file.stat().st_size

                    if file_size >= 600:  # Our minimum size threshold
                        # Verify quality by loading and checking content
                        try:
                            with open(output_file, 'r') as f:
                                data = json.load(f)

                            # Check for essential data
                            has_constituency = bool(data.get("Constituency Number"))
                            has_candidates = len(data.get("candidates", [])) >= 2
                            has_polling_data = len(data.get("serial_no_wise_details", [])) >= 1

                            if has_constituency and (has_candidates or has_polling_data):
                                self.logger.info(f"✅ Vision extraction successful for AC_{ac_number} - {file_size} bytes")
                                return True
                            else:
                                self.logger.warning(f"⚠️ Vision extraction incomplete for AC_{ac_number} - insufficient data")
                                return False

                        except Exception as e:
                            self.logger.warning(f"⚠️ Vision extraction failed validation for AC_{ac_number}: {e}")
                            return False
                    else:
                        self.logger.warning(f"⚠️ Vision extraction output too small for AC_{ac_number}: {file_size} bytes")
                        return False
                else:
                    self.logger.warning(f"⚠️ Vision extraction produced no output for AC_{ac_number}")
                    return False
            else:
                error_msg = result.stderr[:300] if result.stderr else "Unknown error"
                self.logger.error(f"❌ Vision extraction failed for AC_{ac_number}: {error_msg}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"⏰ Vision extraction timeout for AC_{ac_number}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Vision extraction error for AC_{ac_number}: {e}")
            return False

    def verify_output_quality(self, ac_number: int) -> Dict:
        """Verify the quality of the processed output"""
        output_file = Path(f"parsedData/AC_{ac_number}.json")

        if not output_file.exists():
            return {"valid": False, "reason": "No output file", "file_size": 0}

        file_size = output_file.stat().st_size

        if file_size < 600:
            return {"valid": False, "reason": f"File too small: {file_size} bytes", "file_size": file_size}

        try:
            with open(output_file, 'r') as f:
                data = json.load(f)

            # Quality checks
            quality_score = 0
            issues = []

            # Constituency number (required)
            if data.get("Constituency Number"):
                quality_score += 20
            else:
                issues.append("Missing constituency number")

            # Total electors
            if data.get("Total Number of Electors"):
                quality_score += 15
            else:
                issues.append("Missing total electors")

            # Candidates data
            candidates = data.get("candidates", [])
            if len(candidates) >= 2:
                quality_score += 25
                if len(candidates) >= 5:
                    quality_score += 10  # Bonus for comprehensive data
            else:
                issues.append(f"Insufficient candidates: {len(candidates)}")

            # Polling station data
            polling_data = data.get("serial_no_wise_details", [])
            if len(polling_data) >= 1:
                quality_score += 20
                if len(polling_data) >= 10:
                    quality_score += 10  # Bonus for comprehensive data
            else:
                issues.append("No polling station data")

            # Elected person
            if data.get("Elected Person Name"):
                quality_score += 10
            else:
                issues.append("Missing elected person")

            return {
                "valid": quality_score >= 50,  # 50% threshold
                "quality_score": quality_score,
                "file_size": file_size,
                "issues": issues,
                "candidates_count": len(candidates),
                "polling_stations_count": len(polling_data)
            }

        except Exception as e:
            return {"valid": False, "reason": f"JSON parse error: {e}", "file_size": file_size}

    def run_vision_reprocessing(self):
        """Run vision-only reprocessing on all files in the queue"""
        reprocess_list = self.load_reprocess_queue()

        if not reprocess_list:
            self.logger.info("No files to reprocess.")
            return

        self.logger.info("🚀 STARTING TYPE 3 VISION-ONLY PROCESSING")
        self.logger.info("📋 Strategy: Claude Vision LLM ONLY - No OCR fallback")
        self.logger.info(f"📊 Total files to reprocess: {len(reprocess_list)}")
        self.logger.info("=" * 60)

        progress = {
            "session_start": datetime.now().isoformat(),
            "strategy": "vision_only",
            "total_files": len(reprocess_list),
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "results": []
        }

        for i, file_info in enumerate(reprocess_list, 1):
            ac_number = file_info["ac_number"]

            self.logger.info(f"📊 Progress: {i}/{len(reprocess_list)} - Processing AC_{ac_number}")
            self.logger.info(f"📋 Previous issue: {file_info['reason']}")

            start_time = time.time()
            success = self.vision_extract_only(ac_number)
            processing_time = time.time() - start_time

            # Verify output quality
            quality_check = self.verify_output_quality(ac_number)

            result = {
                "ac_number": ac_number,
                "original_issue": file_info["reason"],
                "success": success,
                "processing_time": processing_time,
                "quality_check": quality_check,
                "timestamp": datetime.now().isoformat()
            }

            progress["results"].append(result)
            progress["processed"] += 1

            if success and quality_check["valid"]:
                progress["successful"] += 1
                self.logger.info(f"✅ AC_{ac_number} reprocessed successfully - Quality: {quality_check['quality_score']}/100, Size: {quality_check['file_size']} bytes")
            else:
                progress["failed"] += 1
                reason = quality_check.get("reason", "Unknown")
                self.logger.error(f"❌ AC_{ac_number} reprocessing failed - {reason}")

            # Save progress after each file
            with open(self.reprocess_progress_file, 'w') as f:
                json.dump(progress, f, indent=2)

            # Short delay between files to avoid API rate limits
            time.sleep(2)

        # Final summary
        success_rate = (progress["successful"] / progress["total_files"]) * 100

        self.logger.info("=" * 60)
        self.logger.info("🎉 TYPE 3 VISION-ONLY PROCESSING COMPLETED!")
        self.logger.info("=" * 60)
        self.logger.info(f"Strategy: Claude Vision LLM only (no OCR)")
        self.logger.info(f"Total files: {progress['total_files']}")
        self.logger.info(f"Successful: {progress['successful']}")
        self.logger.info(f"Failed: {progress['failed']}")
        self.logger.info(f"Success rate: {success_rate:.1f}%")

        # Update tracking.json with final results
        self.update_tracking_with_results(progress)

        return progress

    def update_tracking_with_results(self, progress: Dict):
        """Update tracking.json with final reprocessing results"""
        try:
            tracking_file = Path("tracking.json")
            if not tracking_file.exists():
                return

            with open(tracking_file, 'r') as f:
                tracking_data = json.load(f)

            # Create lookup for results
            results_lookup = {r["ac_number"]: r for r in progress["results"]}

            # Update PDF records
            for pdf_record in tracking_data.get("pdfs", []):
                ac_number = pdf_record.get("ac_number")

                if ac_number in results_lookup:
                    result = results_lookup[ac_number]
                    quality_check = result.get("quality_check", {})

                    if result["success"] and quality_check.get("valid", False):
                        pdf_record["status"] = "completed"
                        pdf_record["vision_reprocessing"] = {
                            "success": True,
                            "quality_score": quality_check.get("quality_score", 0),
                            "file_size": quality_check.get("file_size", 0),
                            "processing_time": result.get("processing_time", 0),
                            "reprocessed_timestamp": result.get("timestamp")
                        }
                    else:
                        pdf_record["status"] = "failed"
                        pdf_record["vision_reprocessing"] = {
                            "success": False,
                            "reason": quality_check.get("reason", "Unknown"),
                            "processing_time": result.get("processing_time", 0),
                            "failed_timestamp": result.get("timestamp")
                        }

            # Update summary
            tracking_data["last_vision_reprocessing"] = {
                "timestamp": datetime.now().isoformat(),
                "strategy": "vision_only",
                "total_files": progress["total_files"],
                "successful": progress["successful"],
                "failed": progress["failed"],
                "success_rate": f"{(progress['successful'] / progress['total_files']) * 100:.1f}%"
            }

            # Save updated tracking
            with open(tracking_file, 'w') as f:
                json.dump(tracking_data, f, indent=2, ensure_ascii=False)

            self.logger.info("💾 Updated tracking.json with reprocessing results")

        except Exception as e:
            self.logger.error(f"❌ Failed to update tracking.json: {e}")

def main():
    processor = Type3Processor()

    if len(sys.argv) > 1:
        if sys.argv[1] == "--start":
            processor.run_vision_reprocessing()
        elif sys.argv[1] == "--help":
            print("Usage:")
            print("  python type3_processor.py --start  # Start Type 3 vision-only processing")
            print("  python type3_processor.py --help   # Show this help")
        else:
            print("Invalid argument. Use --help for usage information.")
    else:
        print("Use --start to begin Type 3 vision-only processing or --help for usage.")

if __name__ == "__main__":
    main()