#!/usr/bin/env python3
"""
Gemini Vision LLM extractor for Type 3 PDFs - PARALLEL VERSION
Uses Google Gemini API with ThreadPoolExecutor for faster processing
"""
import json
import os
import sys
from pathlib import Path
from pdf2image import convert_from_path
from google import genai
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

# Increase PIL image size limit to handle large PDFs
Image.MAX_IMAGE_PIXELS = None  # Disable decompression bomb protection

# Set up Gemini client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY environment variable not set.")
    print("Please set it: export GEMINI_API_KEY='your-api-key-here'")
    sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

# Thread-safe lock for progress saving
progress_lock = threading.Lock()

def extract_form20_with_gemini_vision(image_path, page_num, total_pages):
    """Extract Form 20 data using Gemini Vision LLM - single page"""

    import re

    try:
        print(f"\n{'='*60}")
        print(f"📄 PAGE {page_num}/{total_pages} (Thread: {threading.current_thread().name})")
        print(f"{'='*60}")

        # Load image
        print(f"📂 Loading image: {image_path.name}")
        image = Image.open(image_path)
        print(f"✅ Image loaded successfully ({image.size[0]}x{image.size[1]} pixels)")

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

        print(f"🤖 Calling Gemini 2.5 Pro API...")
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
        print(f"❌ Error with Gemini Vision API: {e}")
        import traceback
        traceback.print_exc()
        return (page_num, None)

def save_progress(ac_number, combined_data, pages_processed, last_page):
    """Thread-safe progress saving"""
    with progress_lock:
        Path("parsedData").mkdir(exist_ok=True)
        progress_file = f"parsedData/AC_{ac_number}_progress.json"
        temp_data = combined_data.copy()
        temp_data["pages_processed_so_far"] = pages_processed
        temp_data["last_page_completed"] = last_page
        with open(progress_file, 'w') as f:
            json.dump(temp_data, f, indent=2)
        print(f"💾 Progress saved to {progress_file}")

def process_type3_pdf_with_gemini_vision_parallel(ac_number, max_workers=4):
    """Process a single Type 3 PDF using Gemini Vision LLM with parallel processing"""

    # Find PDF file
    base_dir = Path("VIDHANSABHA_2024")
    pdf_path = None

    for district_dir in base_dir.iterdir():
        if district_dir.is_dir():
            for pdf_file in district_dir.glob(f"AC_{ac_number:02d}.pdf"):
                pdf_path = pdf_file
                break
        if pdf_path:
            break

    if not pdf_path or not pdf_path.exists():
        print(f"❌ PDF not found for AC_{ac_number}")
        return False

    print(f"🔍 PROCESSING AC_{ac_number} WITH GEMINI VISION LLM (PARALLEL MODE)")
    print(f"📁 PDF: {pdf_path}")
    print(f"🧵 Max parallel workers: {max_workers}")

    try:
        # Convert PDF to images
        output_dir = Path(f"vision_pages/AC_{ac_number}")
        output_dir.mkdir(parents=True, exist_ok=True)

        print("📄 Converting PDF to images...")
        images = convert_from_path(str(pdf_path), dpi=300)
        print(f"📊 Converted {len(images)} pages")

        page_files = []
        for i, image in enumerate(images):
            page_file = output_dir / f"page_{i+1:02d}.png"
            image.save(str(page_file), 'PNG', quality=95)
            page_files.append(page_file)
            print(f"💾 Saved: {page_file}")

        # Process all pages except last 2 (summary pages)
        pages_to_process = page_files[:-2] if len(page_files) > 2 else page_files

        print(f"\n🚀 Processing {len(pages_to_process)} pages in parallel...")

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
                executor.submit(extract_form20_with_gemini_vision, page_file, i+1, len(pages_to_process)): i
                for i, page_file in enumerate(pages_to_process)
            }

            # Collect results as they complete
            for future in as_completed(futures):
                page_num, page_data = future.result()

                if page_data:
                    page_results[page_num] = page_data
                    pages_processed += 1
                    print(f"\n✅ Page {page_num} COMPLETED successfully! ({pages_processed}/{len(pages_to_process)})")
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
        print(f"📊 Total polling stations collected: {total_stations}")

        if pages_processed > 0:
            print(f"\n✅ Successfully processed {pages_processed}/{len(pages_to_process)} pages")

            # Save complete extraction
            output_file = f"parsedData/AC_{ac_number}.json"
            combined_data["extraction_method"] = "gemini_vision_llm_parallel"
            combined_data["api_model"] = "gemini-2.5-pro"
            combined_data["pages_available"] = len(page_files)
            combined_data["pages_processed"] = pages_processed
            combined_data["pages_skipped"] = len(page_files) - len(pages_to_process)
            combined_data["parallel_workers"] = max_workers

            # Ensure parsedData directory exists
            Path("parsedData").mkdir(exist_ok=True)

            with open(output_file, 'w') as f:
                json.dump(combined_data, f, indent=2)

            print(f"\n💾 Results saved: {output_file}")
            print(f"📊 Constituency: {combined_data.get('Constituency Number')} - {combined_data.get('constituency_name', 'Unknown')}")
            electors = combined_data.get('Total Number of Electors')
            if electors:
                print(f"📊 Total Electors: {electors:,}")
            else:
                print(f"📊 Total Electors: None")
            print(f"📊 Polling Stations: {len(combined_data.get('serial_no_wise_details', []))}")
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
        print("Usage: python gemini_vision_extractor_parallel.py <AC_NUMBER> [max_workers]")
        print("Example: python gemini_vision_extractor_parallel.py 39 4")
        sys.exit(1)

    ac_number = int(sys.argv[1])
    max_workers = int(sys.argv[2]) if len(sys.argv) > 2 else 4

    success = process_type3_pdf_with_gemini_vision_parallel(ac_number, max_workers)
    sys.exit(0 if success else 1)
