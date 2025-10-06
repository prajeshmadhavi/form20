#!/usr/bin/env python3
"""
Claude Vision LLM extractor for Type 3 PDFs
Uses Anthropic API to extract Form 20 data from PDF images
"""
import json
import os
import sys
import base64
from pathlib import Path
from pdf2image import convert_from_path
import anthropic

# Set up Anthropic client
# Get API key from environment variable
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    print("⚠️ ANTHROPIC_API_KEY environment variable not set.")
    print("Please set it: export ANTHROPIC_API_KEY='your-api-key-here'")
    sys.exit(1)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def image_to_base64(image_path):
    """Convert image to base64 for Claude Vision API"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_form20_with_claude_vision(image_path):
    """Extract Form 20 data using Claude Vision LLM"""

    image_base64 = image_to_base64(image_path)

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
    """

    try:
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=4000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )

        response_text = response.content[0].text

        # Extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            return None

    except Exception as e:
        print(f"Error with Claude Vision API: {e}")
        return None

def process_type3_pdf_with_claude_vision(ac_number):
    """Process a single Type 3 PDF using Claude Vision LLM"""

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

    print(f"🔍 PROCESSING AC_{ac_number} WITH CLAUDE VISION LLM")
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
        # Skip last 2 pages as they may contain summary data
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
            print(f"🤖 Analyzing page {i+1}/{len(pages_to_process)} with Claude Vision LLM...")
            page_data = extract_form20_with_claude_vision(page_file)

            if page_data:
                print(f"✅ Page {i+1} analysis successful!")
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

                # Merge polling station details from all pages
                if page_data.get("serial_no_wise_details"):
                    combined_data["serial_no_wise_details"].extend(page_data["serial_no_wise_details"])
                    print(f"📊 Page {i+1}: Added {len(page_data['serial_no_wise_details'])} polling stations")
            else:
                print(f"⚠️ Page {i+1} analysis failed, continuing...")

        if pages_processed > 0:
            print(f"✅ Successfully processed {pages_processed}/{len(pages_to_process)} pages")

            # Save complete extraction
            output_file = f"parsedData/AC_{ac_number}_CLAUDE_VISION.json"
            combined_data["extraction_method"] = "claude_vision_llm"
            combined_data["api_model"] = "claude-3-7-sonnet-20250219"
            combined_data["pages_available"] = len(page_files)
            combined_data["pages_processed"] = pages_processed
            combined_data["pages_skipped"] = len(page_files) - len(pages_to_process)

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
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            ac_number = int(sys.argv[1])
            success = process_type3_pdf_with_claude_vision(ac_number)
            if success:
                print(f"✅ AC_{ac_number} processing completed successfully")
            else:
                print(f"❌ AC_{ac_number} processing failed")
        except ValueError:
            print("Usage: python claude_vision_extractor.py <AC_NUMBER>")
            print("Example: python claude_vision_extractor.py 1")
    else:
        print("Usage: python claude_vision_extractor.py <AC_NUMBER>")
        print("Example: python claude_vision_extractor.py 1")