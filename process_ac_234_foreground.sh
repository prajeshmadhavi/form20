#!/bin/bash

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Activate virtual environment
source venv/bin/activate

echo "=========================================="
echo "PROCESSING AC_234 - Latur Rural (Latur)"
echo "=========================================="
echo "PDF: VIDHANSABHA_2024/Latur/AC_234.pdf"
echo "PDF Size: 9.5 MB"
echo "Start Time: $(date)"
echo "=========================================="
echo ""

# Run with live output
python gemini_vision_extractor.py 234

EXIT_CODE=$?

echo ""
echo "=========================================="
echo "AC_234 Processing Complete"
echo "End Time: $(date)"
echo "Exit Code: $EXIT_CODE"
echo "=========================================="

if [ $EXIT_CODE -eq 0 ]; then
    if [ -f "parsedData/AC_234.json" ]; then
        SIZE=$(ls -lh parsedData/AC_234.json | awk '{print $5}')
        STATIONS=$(grep -o '"Serial No. Of Polling Station"' parsedData/AC_234.json | wc -l)
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
