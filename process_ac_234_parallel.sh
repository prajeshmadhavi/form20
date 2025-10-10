#!/bin/bash

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Activate virtual environment
source venv/bin/activate

echo "=================================="
echo "PROCESSING AC_234 - Latur Rural (PARALLEL)"
echo "=================================="
echo "PDF: VIDHANSABHA_2024/Latur/AC_234.pdf"
echo "Workers: 4 parallel threads"
echo "Start: $(date)"
echo ""

python gemini_vision_extractor_parallel.py 234 4

EXIT_CODE=$?

echo ""
echo "Finished at: $(date)"
echo "Exit code: $EXIT_CODE"
echo "=================================="

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ AC_234 processed successfully!"

    # Check if JSON was created
    if [ -f "parsedData/AC_234.json" ]; then
        echo "✅ JSON file created: parsedData/AC_234.json"
        ls -lh parsedData/AC_234.json
    else
        echo "⚠️ JSON file not found"
    fi
else
    echo "❌ AC_234 processing failed"
fi

exit $EXIT_CODE
