#!/bin/bash

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Activate virtual environment
source venv/bin/activate

echo "=================================="
echo "PROCESSING REMAINING 2 PDFs"
echo "=================================="
echo ""

# Process AC_113
echo "[1/2] Processing AC_113 - Nandgaon (Nashik)..."
echo "PDF: VIDHANSABHA_2024/Nashik/AC_113.pdf"
echo "Start: $(date)"
echo ""

python gemini_vision_extractor.py 113

AC_113_EXIT=$?

echo ""
echo "Finished AC_113 at: $(date)"
echo "Exit code: $AC_113_EXIT"
echo ""
echo "=================================="
echo ""

# Small delay
sleep 3

# Process AC_234
echo "[2/2] Processing AC_234 - Latur Rural (Latur)..."
echo "PDF: VIDHANSABHA_2024/Latur/AC_234.pdf"
echo "Start: $(date)"
echo ""

python gemini_vision_extractor.py 234

AC_234_EXIT=$?

echo ""
echo "Finished AC_234 at: $(date)"
echo "Exit code: $AC_234_EXIT"
echo ""
echo "=================================="
echo "FINAL SUMMARY"
echo "=================================="
echo "AC_113 exit code: $AC_113_EXIT"
echo "AC_234 exit code: $AC_234_EXIT"

if [ $AC_113_EXIT -eq 0 ] && [ $AC_234_EXIT -eq 0 ]; then
    echo "✅ Both PDFs processed successfully!"
    exit 0
else
    echo "⚠️ One or more PDFs had issues"
    exit 1
fi
