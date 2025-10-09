#!/usr/bin/env python3
"""
Gemini Vision LLM extractor for Type 3 PDFs
Uses Google Gemini API to extract Form 20 data from PDF images
"""
import json
import os
import sys
from pathlib import Path
from pdf2image import convert_from_path
from google import genai
from PIL import Image

# Set up Gemini client
# Get API key from environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY environment variable not set.")
    print("Please set it: export GEMINI_API_KEY='your-api-key-here'")
    sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

def extract_form20_with_gemini_vision(image_path, page_num, total_pages):
    """Extract Form 20 data using Gemini Vision LLM - one page at a time"""

    import time
    import re

    try:
        print(f"\n{'='*60}")
        print(f"📄 PAGE {page_num}/{total_pages}")
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
            return data
        else:
            # Try to parse entire response as JSON
            try:
                data = json.loads(response_text)
                print(f"✅ JSON parsed successfully")
                return data
            except:
                print(f"⚠️ Could not extract JSON from response")
                print(f"Response preview: {response_text[:200]}...")
                return None

    except Exception as e:
        print(f"❌ Error with Gemini Vision API: {e}")
        import traceback
        traceback.print_exc()
        return None

def process_type3_pdf_with_gemini_vision(ac_number):
    """Process a single Type 3 PDF using Gemini Vision LLM"""

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

    print(f"🔍 PROCESSING AC_{ac_number} WITH GEMINI VISION LLM")
    print(f"📁 PDF: {pdf_path}")

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

        print(f"🤖 Processing {len(pages_to_process)} pages (skipping last 2 if present)...")

        combined_data = {
            "Constituency Number": None,
            "constituency_name": None,
            "Total Number of Electors": None,
            "serial_no_wise_details": [],
            "candidates": [],
            "candidate_names": []
        }

        pages_processed = 0

        for i, page_file in enumerate(pages_to_process):
            # Process one page at a time
            page_data = extract_form20_with_gemini_vision(page_file, i+1, len(pages_to_process))

            if page_data:
                print(f"✅ Page {i+1} COMPLETED successfully!")
                pages_processed += 1

                # Extract constituency info from first page
                if i == 0:
                    combined_data["Constituency Number"] = page_data.get("Constituency Number")
                    combined_data["constituency_name"] = page_data.get("constituency_name")
                    combined_data["Total Number of Electors"] = page_data.get("Total Number of Electors")

                    # Get candidate names from first page
                    if page_data.get("candidates"):
                        combined_data["candidates"] = page_data["candidates"]
                        combined_data["candidate_names"] = [c.get("candidate_name", "") for c in page_data["candidates"]]

                    print(f"\n📋 CONSTITUENCY INFO:")
                    print(f"   Number: {combined_data.get('Constituency Number', 'N/A')}")
                    print(f"   Name: {combined_data.get('constituency_name', 'N/A')}")
                    electors = combined_data.get('Total Number of Electors')
                    print(f"   Electors: {electors:,}" if electors else "   Electors: N/A")
                    print(f"   Candidates: {len(combined_data.get('candidates', []))}")

                # Merge polling station details from all pages
                if page_data.get("serial_no_wise_details"):
                    combined_data["serial_no_wise_details"].extend(page_data["serial_no_wise_details"])
                    total_stations = len(combined_data["serial_no_wise_details"])
                    print(f"📊 Total polling stations collected so far: {total_stations}")

                # Save progress after each page
                Path("parsedData").mkdir(exist_ok=True)
                progress_file = f"parsedData/AC_{ac_number}_progress.json"
                with open(progress_file, 'w') as f:
                    temp_data = combined_data.copy()
                    temp_data["pages_processed_so_far"] = pages_processed
                    temp_data["last_page_completed"] = i + 1
                    json.dump(temp_data, f, indent=2)
                print(f"💾 Progress saved to {progress_file}")
            else:
                print(f"⚠️ Page {i+1} analysis FAILED, continuing to next page...")

            # Small delay between API calls
            import time
            if i < len(pages_to_process) - 1:  # Don't delay after last page
                print(f"⏸️  Waiting 2 seconds before next page...")
                time.sleep(2)

        if pages_processed > 0:
            print(f"✅ Successfully processed {pages_processed}/{len(pages_to_process)} pages")

            # Save complete extraction
            output_file = f"parsedData/AC_{ac_number}.json"
            combined_data["extraction_method"] = "gemini_vision_llm"
            combined_data["api_model"] = "gemini-2.5-pro"
            combined_data["pages_available"] = len(page_files)
            combined_data["pages_processed"] = pages_processed
            combined_data["pages_skipped"] = len(page_files) - len(pages_to_process)

            # Ensure parsedData directory exists
            Path("parsedData").mkdir(exist_ok=True)

            with open(output_file, 'w') as f:
                json.dump(combined_data, f, indent=2)

            print(f"💾 Results saved: {output_file}")
            print(f"📊 Constituency: {combined_data.get('Constituency Number')} - {combined_data.get('constituency_name', 'Unknown')}")
            print(f"📊 Total Electors: {combined_data.get('Total Number of Electors', 'None'):,}" if combined_data.get('Total Number of Electors') else "📊 Total Electors: None")
            print(f"📊 Polling Stations: {len(combined_data.get('serial_no_wise_details', []))}")
            print(f"📊 Candidates: {len(combined_data.get('candidates', []))}")

            if combined_data.get('Elected Person Name'):
                print(f"🏆 Winner: {combined_data['Elected Person Name']} ({combined_data.get('elected_person_votes', 0):,} votes)")

            return True
        else:
            print("❌ All page analyses failed")
            return False

    except Exception as e:
        print(f"❌ Error processing AC_{ac_number}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            ac_number = int(sys.argv[1])
            success = process_type3_pdf_with_gemini_vision(ac_number)
            if success:
                print(f"✅ AC_{ac_number} processing completed successfully")
            else:
                print(f"❌ AC_{ac_number} processing failed")
        except ValueError:
            print("Usage: python gemini_vision_extractor.py <AC_NUMBER>")
            print("Example: python gemini_vision_extractor.py 1")
    else:
        print("Usage: python gemini_vision_extractor.py <AC_NUMBER>")
        print("Example: python gemini_vision_extractor.py 1")
