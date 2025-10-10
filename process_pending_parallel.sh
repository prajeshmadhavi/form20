#!/bin/bash

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Activate virtual environment
source venv/bin/activate

echo "=================================="
echo "PROCESSING PENDING ACs WITH PARALLEL MODE"
echo "=================================="
echo "Start: $(date)"
echo ""

# Read pending files
PENDING_FILES=$(cat pending_files_list.txt)

for AC in $PENDING_FILES; do
    echo ""
    echo "=========================================="
    echo "Processing AC_${AC}"
    echo "=========================================="

    # Use 3 workers to avoid rate limiting
    python gemini_vision_extractor_parallel.py $AC 3

    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ AC_${AC} completed successfully"

        # Verify JSON file
        if [ -f "parsedData/AC_${AC}.json" ]; then
            SIZE=$(stat -c%s "parsedData/AC_${AC}.json")
            if [ $SIZE -gt 600 ]; then
                echo "✅ JSON file valid: parsedData/AC_${AC}.json (${SIZE} bytes)"
            else
                echo "⚠️ JSON file too small: ${SIZE} bytes"
            fi
        fi
    else
        echo "❌ AC_${AC} failed with exit code ${EXIT_CODE}"
    fi

    # Wait 10 seconds between files to avoid rate limiting
    echo "⏸️  Waiting 10 seconds before next AC..."
    sleep 10
done

echo ""
echo "=================================="
echo "ALL PENDING FILES PROCESSED"
echo "Finished at: $(date)"
echo "=================================="
