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
ANTHROPIC_API_KEY = "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"
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
    5. Calculate total votes for each candidate across all polling stations
    6. Identify the elected person (candidate with highest votes)

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
                "candidate_name": "<actual name from header>",
                "Total Votes Polled": <total across all stations>
            }
        ],
        "Elected Person Name": "<winner name>",
        "elected_person_votes": <winner total votes>
    }

    Read the table carefully and extract all visible polling station data. Pay attention to candidate names in the column headers.
    """

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
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

        # Process first page with Claude Vision
        print(f"🤖 Analyzing page 1 with Claude Vision LLM...")
        first_page_data = extract_form20_with_claude_vision(page_files[0])

        if first_page_data:
            print("✅ Claude Vision analysis successful!")

            # Save complete extraction
            output_file = f"parsedData/AC_{ac_number}_CLAUDE_VISION.json"
            first_page_data["extraction_method"] = "claude_vision_llm"
            first_page_data["api_model"] = "claude-3-5-sonnet-20241022"
            first_page_data["pages_available"] = len(page_files)
            first_page_data["pages_processed"] = 1

            with open(output_file, 'w') as f:
                json.dump(first_page_data, f, indent=2)

            print(f"💾 Results saved: {output_file}")
            print(f"📊 Constituency: {first_page_data.get('Constituency Number')} - {first_page_data.get('constituency_name', 'Unknown')}")
            print(f"📊 Total Electors: {first_page_data.get('Total Number of Electors', 'None'):,}" if first_page_data.get('Total Number of Electors') else "📊 Total Electors: None")
            print(f"📊 Polling Stations: {len(first_page_data.get('serial_no_wise_details', []))}")
            print(f"📊 Candidates: {len(first_page_data.get('candidates', []))}")

            if first_page_data.get('Elected Person Name'):
                print(f"🏆 Winner: {first_page_data['Elected Person Name']} ({first_page_data.get('elected_person_votes', 0):,} votes)")

            return True
        else:
            print("❌ Claude Vision analysis failed")
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