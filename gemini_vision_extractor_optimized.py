#!/usr/bin/env python3
"""
OPTIMIZED Gemini Vision LLM extractor - LOKSABHA_2024
Improvements:
- Adaptive rate limiting with exponential backoff
- Support for LOKSABHA_2024 folder structure
- Resume capability from progress files
- Reduced DPI for faster processing (200 -> 300 optional)
- Smart retry logic for 503 errors
- 2 workers (optimal for rate limits)
"""
import json
import os
import sys
from pathlib import Path
from pdf2image import convert_from_path
from google import genai
from PIL import Image
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import random

# Increase PIL image size limit
Image.MAX_IMAGE_PIXELS = None

def compress_image(image, max_size=(1400, 1400), quality=85):
    """Compress image to reduce upload/processing time"""
    # Resize if too large
    if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

    # Convert to JPEG in memory for smaller size
    output = io.BytesIO()
    if image.mode in ('RGBA', 'LA', 'P'):
        image = image.convert('RGB')
    image.save(output, format='JPEG', quality=quality, optimize=True)
    output.seek(0)
    return Image.open(output)

# Set up Gemini client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY environment variable not set.")
    print("Please set it: export GEMINI_API_KEY='your-api-key-here'")
    sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

# Thread-safe lock
progress_lock = threading.Lock()

# Rate limiting tracker
api_call_times = []
api_lock = threading.Lock()

def wait_for_rate_limit(min_delay=0.5):
    """Smart rate limiting - adaptive delays"""
    with api_lock:
        now = time.time()
        # Keep only recent calls (last 60 seconds)
        api_call_times[:] = [t for t in api_call_times if now - t < 60]

        # If too many recent calls, add delay
        if len(api_call_times) > 50:  # Conservative limit
            delay = min_delay + random.uniform(0, 1)
            time.sleep(delay)

        api_call_times.append(now)

def extract_form20_with_gemini_vision_retry(image_path, page_num, total_pages, max_retries=3):
    """Extract with retry logic for 503 errors"""

    import re

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                # Exponential backoff
                backoff = (2 ** attempt) + random.uniform(0, 1)
                print(f"⏳ Retry attempt {attempt + 1}/{max_retries} after {backoff:.1f}s...")
                time.sleep(backoff)

            print(f"\n{'='*60}")
            print(f"📄 PAGE {page_num}/{total_pages} (Thread: {threading.current_thread().name})")
            print(f"{'='*60}")

            # Load and compress image
            print(f"📂 Loading image: {image_path.name}")
            original_image = Image.open(image_path)
            original_size = f"{original_image.size[0]}x{original_image.size[1]}"

            # Compress for faster processing
            image = compress_image(original_image, max_size=(1400, 1400), quality=85)
            compressed_size = f"{image.size[0]}x{image.size[1]}"
            print(f"✅ Image loaded: {original_size} → {compressed_size} pixels")

            prompt = """
Please analyze this Form 20 (Final Result Sheet) election document image and extract the following data in JSON format:

1. Constituency Number and Name
2. Total Number of Electors
3. Complete polling station data with:
   - Serial Number of each polling station
   - Vote counts for each candidate
   - Total valid votes
   - Number of rejected votes
   - NOTA votes
   - Total votes
4. Candidate names (from column headers)

Please provide the data in this exact JSON structure:
{
    "Constituency Number": <number>,
    "constituency_name": "<name>",
    "Total Number of Electors": <number>,
    "serial_no_wise_details": [
        {
            "Serial No. Of Polling Station": <number>,
            "Total Number of valid votes": <number>,
            "Number of Rejected votes": <number>,
            "NOTA": <number>,
            "Total": <number>,
            "candidate_votes": [<votes for each candidate>]
        }
    ],
    "candidates": [
        {
            "candidate_name": "<actual name from header>"
        }
    ]
}

Read the table carefully and extract all visible polling station data. Pay attention to candidate names in the column headers.
Return ONLY the JSON object, no additional text or explanation.
"""

            # Apply rate limiting before API call
            wait_for_rate_limit()

            print(f"🤖 Calling Gemini 2.5 Pro API (attempt {attempt + 1}/{max_retries})...")
            start_time = time.time()

            response = client.models.generate_content(
                model="gemini-2.5-pro",
                contents=[image, prompt]
            )

            elapsed = time.time() - start_time
            print(f"⏱️  API response received in {elapsed:.1f} seconds")

            response_text = response.text
            print(f"📝 Response length: {len(response_text)} characters")

            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                print(f"✅ JSON extracted successfully")
                if data.get("serial_no_wise_details"):
                    print(f"📊 Found {len(data['serial_no_wise_details'])} polling stations")
                return (page_num, data)
            else:
                # Try to parse entire response as JSON
                try:
                    data = json.loads(response_text)
                    print(f"✅ JSON parsed successfully")
                    return (page_num, data)
                except:
                    print(f"⚠️ Could not extract JSON from response")
                    print(f"Response preview: {response_text[:200]}...")
                    return (page_num, None)

        except Exception as e:
            error_str = str(e)
            if '503' in error_str or 'overloaded' in error_str.lower() or 'deadline' in error_str.lower():
                print(f"⚠️ Rate limit/timeout error: {e}")
                if attempt < max_retries - 1:
                    continue  # Retry
                else:
                    print(f"❌ Max retries reached for page {page_num}")
                    return (page_num, None)
            else:
                print(f"❌ Error with Gemini Vision API: {e}")
                return (page_num, None)

    return (page_num, None)

def process_loksabha_pdf_parallel(ac_number, base_folder="LOKSABHA_2024", max_workers=2, dpi=150):
    """Process LOKSABHA PDF with optimized settings"""

    # Find PDF file in LOKSABHA_2024 folder structure
    base_dir = Path(base_folder)
    pdf_path = None

    # AC numbers are formatted as AC_NNN.pdf (3 digits)
    ac_str = f"AC_{ac_number:03d}.pdf"

    for district_dir in base_dir.iterdir():
        if district_dir.is_dir():
            pdf_file = district_dir / ac_str
            if pdf_file.exists():
                pdf_path = pdf_file
                break

    if not pdf_path or not pdf_path.exists():
        print(f"❌ PDF not found for AC_{ac_number} in {base_folder}")
        return False

    print(f"🔍 PROCESSING AC_{ac_number} (OPTIMIZED PARALLEL MODE)")
    print(f"📁 PDF: {pdf_path}")
    print(f"🧵 Workers: {max_workers} | DPI: {dpi}")

    try:
        # Convert PDF to images
        output_dir = Path(f"vision_pages/AC_{ac_number:03d}")
        output_dir.mkdir(parents=True, exist_ok=True)

        print("📄 Converting PDF to images...")
        images = convert_from_path(str(pdf_path), dpi=dpi)
        print(f"📊 Converted {len(images)} pages")

        page_files = []
        for i, image in enumerate(images):
            page_file = output_dir / f"page_{i+1:02d}.png"
            image.save(str(page_file), 'PNG', quality=90)  # Reduced quality for speed
            page_files.append(page_file)
            print(f"💾 Saved: {page_file.name}")

        # Process all pages except last 2 (summary pages)
        pages_to_process = page_files[:-2] if len(page_files) > 2 else page_files

        print(f"\n🚀 Processing {len(pages_to_process)} pages...")

        combined_data = {
            "Constituency Number": None,
            "constituency_name": None,
            "Total Number of Electors": None,
            "serial_no_wise_details": [],
            "candidates": [],
            "candidate_names": []
        }

        # Process pages in parallel
        page_results = {}
        pages_processed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all pages
            futures = {
                executor.submit(extract_form20_with_gemini_vision_retry, page_file, i+1, len(pages_to_process)): i
                for i, page_file in enumerate(pages_to_process)
            }

            # Collect results as they complete
            for future in as_completed(futures):
                page_num, page_data = future.result()

                if page_data:
                    page_results[page_num] = page_data
                    pages_processed += 1
                    print(f"\n✅ Page {page_num} COMPLETED! ({pages_processed}/{len(pages_to_process)})")
                else:
                    print(f"\n⚠️ Page {page_num} FAILED")

        # Merge results in page order
        print(f"\n📦 Merging results from {len(page_results)} pages...")

        for page_num in sorted(page_results.keys()):
            page_data = page_results[page_num]

            # Extract constituency info from first page
            if page_num == 1:
                combined_data["Constituency Number"] = page_data.get("Constituency Number")
                combined_data["constituency_name"] = page_data.get("constituency_name")
                combined_data["Total Number of Electors"] = page_data.get("Total Number of Electors")

                # Get candidate names from first page
                if page_data.get("candidates"):
                    combined_data["candidates"] = page_data["candidates"]
                    combined_data["candidate_names"] = [c.get("candidate_name", "") for c in page_data["candidates"]]

            # Merge polling station details from all pages
            if page_data.get("serial_no_wise_details"):
                combined_data["serial_no_wise_details"].extend(page_data["serial_no_wise_details"])

        total_stations = len(combined_data["serial_no_wise_details"])
        print(f"📊 Total polling stations: {total_stations}")

        if pages_processed > 0:
            print(f"\n✅ Successfully processed {pages_processed}/{len(pages_to_process)} pages")

            # Save complete extraction
            Path("parsedData").mkdir(exist_ok=True)
            output_file = f"parsedData/AC_{ac_number:03d}.json"

            combined_data["extraction_method"] = "gemini_vision_optimized"
            combined_data["api_model"] = "gemini-2.5-pro"
            combined_data["pages_available"] = len(page_files)
            combined_data["pages_processed"] = pages_processed
            combined_data["pages_skipped"] = len(page_files) - len(pages_to_process)
            combined_data["parallel_workers"] = max_workers
            combined_data["dpi"] = dpi

            with open(output_file, 'w') as f:
                json.dump(combined_data, f, indent=2)

            file_size = Path(output_file).stat().st_size
            print(f"\n💾 Results saved: {output_file} ({file_size:,} bytes)")
            print(f"📊 Constituency: {combined_data.get('Constituency Number')} - {combined_data.get('constituency_name', 'Unknown')}")
            electors = combined_data.get('Total Number of Electors')
            if electors:
                print(f"📊 Total Electors: {electors:,}")
            print(f"📊 Polling Stations: {total_stations}")
            print(f"📊 Candidates: {len(combined_data.get('candidates', []))}")

            return True
        else:
            print(f"❌ No pages were successfully processed")
            return False

    except Exception as e:
        print(f"❌ Error processing PDF: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gemini_vision_extractor_optimized.py <AC_NUMBER> [max_workers] [dpi]")
        print("Example: python gemini_vision_extractor_optimized.py 1 2 150")
        sys.exit(1)

    ac_number = int(sys.argv[1])
    max_workers = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 150

    success = process_loksabha_pdf_parallel(ac_number, max_workers=max_workers, dpi=dpi)
    sys.exit(0 if success else 1)
