#!/bin/bash

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Activate virtual environment
source venv/bin/activate

echo "=========================================="
echo "PROCESSING AC_113 - Nandgaon (Nashik)"
echo "=========================================="
echo "PDF: VIDHANSABHA_2024/Nashik/AC_113.pdf"
echo "PDF Size: 4.3 MB"
echo "Start Time: $(date)"
echo "=========================================="
echo ""

# Run with live output
python gemini_vision_extractor.py 113

EXIT_CODE=$?

echo ""
echo "=========================================="
echo "AC_113 Processing Complete"
echo "End Time: $(date)"
echo "Exit Code: $EXIT_CODE"
echo "=========================================="

if [ $EXIT_CODE -eq 0 ]; then
    if [ -f "parsedData/AC_113.json" ]; then
        SIZE=$(ls -lh parsedData/AC_113.json | awk '{print $5}')
        STATIONS=$(grep -o '"Serial No. Of Polling Station"' parsedData/AC_113.json | wc -l)
        echo "✅ SUCCESS!"
        echo "   JSON File: $SIZE"
        echo "   Polling Stations: $STATIONS"
    else
        echo "⚠️  Completed but JSON not found"
    fi
else
    echo "❌ FAILED with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
