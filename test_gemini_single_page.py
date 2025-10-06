#!/usr/bin/env python3
import json
from google import genai
from PIL import Image

GEMINI_API_KEY = "AIzaSyBeoWVTupDwKCPeewiFX2anlOwJsIPY7wo"
client = genai.Client(api_key=GEMINI_API_KEY)

print("Loading image...")
image = Image.open("vision_pages/AC_1/page_01.png")

print("Calling Gemini 2.5 Pro...")
prompt = "Extract the constituency number and name from this Form 20 document. Return as JSON with fields: Constituency Number, constituency_name"

try:
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=[image, prompt]
    )
    print("Response received:")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
