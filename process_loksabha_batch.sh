#!/bin/bash

# Batch processor for LOKSABHA_2024 PDFs
# Processes AC_001 to AC_288 using optimized parallel extractor

echo "================================================================"
echo "LOKSABHA_2024 BATCH PROCESSING"
echo "================================================================"

# Configuration
MAX_WORKERS=2
DPI=150  # Lower DPI for faster processing
DELAY_BETWEEN_FILES=15  # seconds

# Load API keys from .env
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Loaded and exported API keys from .env"
else
    echo "❌ .env file not found"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if GEMINI_API_KEY is set
if [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ GEMINI_API_KEY not set in .env file"
    exit 1
fi

echo "✅ GEMINI_API_KEY is set: ${GEMINI_API_KEY:0:20}..."

# Process range (can be overridden by command line args)
START_AC=${1:-1}
END_AC=${2:-288}

echo "Processing AC_${START_AC} to AC_${END_AC}"
echo "Workers: ${MAX_WORKERS} | DPI: ${DPI} | Delay: ${DELAY_BETWEEN_FILES}s"
echo ""

TOTAL_COUNT=0
SUCCESS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

for AC_NUM in $(seq $START_AC $END_AC); do
    TOTAL_COUNT=$((TOTAL_COUNT + 1))

    echo ""
    echo "================================================================"
    echo "Processing AC_${AC_NUM} (${TOTAL_COUNT}/$(($END_AC - $START_AC + 1)))"
    echo "================================================================"

    # Check if output already exists and is valid
    OUTPUT_FILE="parsedData/AC_$(printf "%03d" $AC_NUM).json"
    if [ -f "$OUTPUT_FILE" ]; then
        SIZE=$(stat -c%s "$OUTPUT_FILE" 2>/dev/null || echo "0")
        if [ $SIZE -gt 600 ]; then
            echo "✅ Already processed (${SIZE} bytes) - SKIPPING"
            SKIP_COUNT=$((SKIP_COUNT + 1))
            continue
        else
            echo "⚠️  Existing file too small (${SIZE} bytes) - REPROCESSING"
        fi
    fi

    # Process the PDF
    python gemini_vision_extractor_optimized.py $AC_NUM $MAX_WORKERS $DPI
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        # Verify output file
        if [ -f "$OUTPUT_FILE" ]; then
            SIZE=$(stat -c%s "$OUTPUT_FILE")
            if [ $SIZE -gt 600 ]; then
                echo "✅ AC_${AC_NUM} COMPLETED (${SIZE} bytes)"
                SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            else
                echo "⚠️  AC_${AC_NUM} output too small (${SIZE} bytes)"
                FAIL_COUNT=$((FAIL_COUNT + 1))
            fi
        else
            echo "❌ AC_${AC_NUM} output file not found"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
    else
        echo "❌ AC_${AC_NUM} FAILED (exit code: $EXIT_CODE)"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi

    # Progress summary
    echo ""
    echo "Progress: Success=$SUCCESS_COUNT | Failed=$FAIL_COUNT | Skipped=$SKIP_COUNT | Total=$TOTAL_COUNT"

    # Wait before next file (except for last one)
    if [ $AC_NUM -lt $END_AC ]; then
        echo "⏳ Waiting ${DELAY_BETWEEN_FILES}s before next file..."
        sleep $DELAY_BETWEEN_FILES
    fi
done

echo ""
echo "================================================================"
echo "BATCH PROCESSING COMPLETE"
echo "================================================================"
echo "Total Processed: $TOTAL_COUNT"
echo "Successful: $SUCCESS_COUNT"
echo "Failed: $FAIL_COUNT"
echo "Skipped: $SKIP_COUNT"
echo "================================================================"

exit 0
