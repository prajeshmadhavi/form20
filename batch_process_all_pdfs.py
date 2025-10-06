#!/usr/bin/env python3
"""
Batch processor for all 288 PDFs using Gemini Vision LLM
Processes PDFs sequentially from AC_1 to AC_288 with comprehensive logging and tracking
"""
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime
import traceback

# Import the main processor
from gemini_vision_extractor import process_type3_pdf_with_gemini_vision

# Configuration
START_AC = 1
END_AC = 288
TRACKING_FILE = "batch_processing_tracking.json"
LOGS_DIR = Path("batch_logs")
MASTER_LOG = "batch_processing_master.log"

def load_tracking():
    """Load tracking data from JSON file"""
    if Path(TRACKING_FILE).exists():
        with open(TRACKING_FILE, 'r') as f:
            return json.load(f)
    else:
        return {
            "start_time": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "current_ac": START_AC,
            "completed": [],
            "failed": [],
            "skipped": [],
            "in_progress": None,
            "total_processed": 0,
            "total_failed": 0,
            "total_skipped": 0,
            "statistics": {
                "total_polling_stations": 0,
                "total_api_calls": 0,
                "total_processing_time": 0
            }
        }

def save_tracking(tracking_data):
    """Save tracking data to JSON file"""
    tracking_data["last_updated"] = datetime.now().isoformat()
    with open(TRACKING_FILE, 'w') as f:
        json.dump(tracking_data, f, indent=2)

def log_master(message):
    """Log to master log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}\n"
    with open(MASTER_LOG, 'a') as f:
        f.write(log_msg)
    print(message)

def check_pdf_exists(ac_number):
    """Check if PDF file exists for given AC number"""
    base_dir = Path("VIDHANSABHA_2024")
    for district_dir in base_dir.iterdir():
        if district_dir.is_dir():
            pdf_file = district_dir / f"AC_{ac_number:02d}.pdf"
            if pdf_file.exists():
                return True, str(pdf_file)
    return False, None

def process_single_ac(ac_number, tracking_data):
    """Process a single AC with comprehensive logging"""

    log_file = LOGS_DIR / f"AC_{ac_number}_log.txt"
    start_time = time.time()

    log_master(f"\n{'='*80}")
    log_master(f"STARTING AC_{ac_number}")
    log_master(f"{'='*80}")

    # Update tracking
    tracking_data["in_progress"] = ac_number
    tracking_data["current_ac"] = ac_number
    save_tracking(tracking_data)

    # Check if PDF exists
    pdf_exists, pdf_path = check_pdf_exists(ac_number)
    if not pdf_exists:
        log_master(f"⚠️  AC_{ac_number}: PDF file not found - SKIPPING")
        tracking_data["skipped"].append(ac_number)
        tracking_data["total_skipped"] += 1
        tracking_data["in_progress"] = None
        save_tracking(tracking_data)

        # Log to individual file
        with open(log_file, 'w') as f:
            f.write(f"AC_{ac_number} - SKIPPED\n")
            f.write(f"Reason: PDF file not found\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")

        return "skipped"

    log_master(f"📁 AC_{ac_number}: Found PDF at {pdf_path}")

    # Redirect stdout/stderr to log file
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    try:
        with open(log_file, 'w') as f:
            # Write header
            f.write(f"{'='*80}\n")
            f.write(f"AC_{ac_number} Processing Log\n")
            f.write(f"{'='*80}\n")
            f.write(f"Start Time: {datetime.now().isoformat()}\n")
            f.write(f"PDF Path: {pdf_path}\n")
            f.write(f"{'='*80}\n\n")
            f.flush()

            # Redirect output
            sys.stdout = f
            sys.stderr = f

            # Process the PDF
            success = process_type3_pdf_with_gemini_vision(ac_number)

            # Restore output
            sys.stdout = original_stdout
            sys.stderr = original_stderr

            elapsed_time = time.time() - start_time

            if success:
                log_master(f"✅ AC_{ac_number}: COMPLETED in {elapsed_time:.1f} seconds")
                tracking_data["completed"].append(ac_number)
                tracking_data["total_processed"] += 1
                tracking_data["statistics"]["total_processing_time"] += elapsed_time

                # Get polling station count from output file
                try:
                    output_file = f"parsedData/AC_{ac_number}.json"
                    with open(output_file, 'r') as jf:
                        data = json.load(jf)
                        stations = len(data.get("serial_no_wise_details", []))
                        pages = data.get("pages_processed", 0)
                        tracking_data["statistics"]["total_polling_stations"] += stations
                        tracking_data["statistics"]["total_api_calls"] += pages
                        log_master(f"📊 AC_{ac_number}: {stations} polling stations, {pages} pages processed")
                except:
                    pass

                # Append summary to log file
                with open(log_file, 'a') as f:
                    f.write(f"\n{'='*80}\n")
                    f.write(f"Status: SUCCESS\n")
                    f.write(f"Processing Time: {elapsed_time:.1f} seconds\n")
                    f.write(f"End Time: {datetime.now().isoformat()}\n")
                    f.write(f"{'='*80}\n")

                tracking_data["in_progress"] = None
                save_tracking(tracking_data)
                return "success"
            else:
                log_master(f"❌ AC_{ac_number}: FAILED after {elapsed_time:.1f} seconds")
                tracking_data["failed"].append(ac_number)
                tracking_data["total_failed"] += 1

                # Append failure to log file
                with open(log_file, 'a') as f:
                    f.write(f"\n{'='*80}\n")
                    f.write(f"Status: FAILED\n")
                    f.write(f"Processing Time: {elapsed_time:.1f} seconds\n")
                    f.write(f"End Time: {datetime.now().isoformat()}\n")
                    f.write(f"{'='*80}\n")

                tracking_data["in_progress"] = None
                save_tracking(tracking_data)
                return "failed"

    except Exception as e:
        # Restore output in case of exception
        sys.stdout = original_stdout
        sys.stderr = original_stderr

        elapsed_time = time.time() - start_time
        log_master(f"❌ AC_{ac_number}: EXCEPTION after {elapsed_time:.1f} seconds")
        log_master(f"   Error: {str(e)}")

        tracking_data["failed"].append(ac_number)
        tracking_data["total_failed"] += 1

        # Log exception details
        with open(log_file, 'a') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Status: EXCEPTION\n")
            f.write(f"Error: {str(e)}\n")
            f.write(f"Traceback:\n")
            f.write(traceback.format_exc())
            f.write(f"\nProcessing Time: {elapsed_time:.1f} seconds\n")
            f.write(f"End Time: {datetime.now().isoformat()}\n")
            f.write(f"{'='*80}\n")

        tracking_data["in_progress"] = None
        save_tracking(tracking_data)
        return "exception"

def main():
    """Main batch processing function"""

    # Create logs directory
    LOGS_DIR.mkdir(exist_ok=True)

    # Load or create tracking data
    tracking_data = load_tracking()

    log_master(f"\n{'#'*80}")
    log_master(f"# BATCH PROCESSING: AC_{START_AC} to AC_{END_AC}")
    log_master(f"{'#'*80}")
    log_master(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_master(f"Tracking File: {TRACKING_FILE}")
    log_master(f"Logs Directory: {LOGS_DIR}")

    # Resume from last position if interrupted
    start_from = tracking_data.get("current_ac", START_AC)
    if start_from > START_AC:
        log_master(f"\n🔄 RESUMING from AC_{start_from}")
        log_master(f"Previously completed: {len(tracking_data['completed'])}")
        log_master(f"Previously failed: {len(tracking_data['failed'])}")
        log_master(f"Previously skipped: {len(tracking_data['skipped'])}")

    # Process all ACs sequentially
    for ac_number in range(start_from, END_AC + 1):

        # Check if already processed
        if ac_number in tracking_data["completed"]:
            log_master(f"⏭️  AC_{ac_number}: Already completed - SKIPPING")
            continue

        if ac_number in tracking_data["skipped"]:
            log_master(f"⏭️  AC_{ac_number}: Already skipped - SKIPPING")
            continue

        # Process this AC
        result = process_single_ac(ac_number, tracking_data)

        # Print progress summary every 10 ACs
        if ac_number % 10 == 0:
            log_master(f"\n📈 PROGRESS SUMMARY (as of AC_{ac_number}):")
            log_master(f"   Completed: {tracking_data['total_processed']}")
            log_master(f"   Failed: {tracking_data['total_failed']}")
            log_master(f"   Skipped: {tracking_data['total_skipped']}")
            log_master(f"   Total Polling Stations: {tracking_data['statistics']['total_polling_stations']}")
            log_master(f"   Total API Calls: {tracking_data['statistics']['total_api_calls']}")
            log_master(f"   Total Processing Time: {tracking_data['statistics']['total_processing_time']/3600:.2f} hours\n")

        # Small delay between ACs to avoid rate limiting
        if ac_number < END_AC:
            time.sleep(3)

    # Final summary
    tracking_data["end_time"] = datetime.now().isoformat()
    save_tracking(tracking_data)

    log_master(f"\n{'#'*80}")
    log_master(f"# BATCH PROCESSING COMPLETE")
    log_master(f"{'#'*80}")
    log_master(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_master(f"\nFINAL STATISTICS:")
    log_master(f"  Total Processed: {tracking_data['total_processed']}")
    log_master(f"  Total Failed: {tracking_data['total_failed']}")
    log_master(f"  Total Skipped: {tracking_data['total_skipped']}")
    log_master(f"  Total Polling Stations: {tracking_data['statistics']['total_polling_stations']}")
    log_master(f"  Total API Calls: {tracking_data['statistics']['total_api_calls']}")
    log_master(f"  Total Processing Time: {tracking_data['statistics']['total_processing_time']/3600:.2f} hours")
    log_master(f"\nCompleted ACs: {sorted(tracking_data['completed'])}")
    log_master(f"Failed ACs: {sorted(tracking_data['failed'])}")
    log_master(f"Skipped ACs: {sorted(tracking_data['skipped'])}")
    log_master(f"\nTracking file saved: {TRACKING_FILE}")
    log_master(f"Individual logs saved in: {LOGS_DIR}/")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_master("\n\n⚠️  INTERRUPTED BY USER (Ctrl+C)")
        log_master("Progress has been saved. Run again to resume.")
        sys.exit(1)
    except Exception as e:
        log_master(f"\n\n❌ FATAL ERROR: {str(e)}")
        log_master(traceback.format_exc())
        sys.exit(1)
