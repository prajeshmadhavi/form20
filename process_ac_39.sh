#!/bin/bash

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Activate virtual environment
source venv/bin/activate

echo "=================================="
echo "PROCESSING AC_39 - Teosa (Amravati)"
echo "=================================="
echo "PDF: VIDHANSABHA_2024/Amravati/AC_39.pdf"
echo "Start: $(date)"
echo ""

python gemini_vision_extractor.py 39

EXIT_CODE=$?

echo ""
echo "Finished at: $(date)"
echo "Exit code: $EXIT_CODE"
echo "=================================="

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ AC_39 processed successfully!"
    
    # Check if JSON was created
    if [ -f "parsedData/AC_39.json" ]; then
        echo "✅ JSON file created: parsedData/AC_39.json"
        ls -lh parsedData/AC_39.json
    else
        echo "⚠️ JSON file not found"
    fi
else
    echo "❌ AC_39 processing failed"
fi

exit $EXIT_CODE
