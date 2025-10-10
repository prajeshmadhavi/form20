#!/bin/bash

# ULTRA-FAST batch processor for LOKSABHA_2024 PDFs
# Uses gemini-2.0-flash with 10 workers per file + 2 files in parallel
# Rate limit: 2,000 RPM

echo "================================================================"
echo "LOKSABHA_2024 ULTRA-FAST BATCH PROCESSING"
echo "================================================================"

# Configuration
MAX_WORKERS=15  # Workers per file (increased from 10)
PARALLEL_FILES=6  # Number of files to process simultaneously (increased from 2)
DPI=120  # Lower DPI for faster processing (reduced from 150)
MODEL="gemini-2.0-flash (2,000 RPM)"

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
echo ""
echo "⚡ ULTRA-FAST Configuration:"
echo "   Model: $MODEL"
echo "   Workers per file: $MAX_WORKERS"
echo "   Parallel files: $PARALLEL_FILES"
echo "   DPI: $DPI"
echo "   Expected speed: ~40-60 seconds per file (vs 20-30 minutes!)"
echo ""

# Process range (can be overridden by command line args)
START_AC=${1:-1}
END_AC=${2:-288}

echo "Processing AC_${START_AC} to AC_${END_AC}"
echo ""

TOTAL_COUNT=0
SUCCESS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

# Track background jobs
declare -a BG_PIDS

# Process files with parallelism
for AC_NUM in $(seq $START_AC $END_AC); do
    # Wait if we have too many parallel jobs
    while [ ${#BG_PIDS[@]} -ge $PARALLEL_FILES ]; do
        # Check which jobs are done
        NEW_PIDS=()
        for PID in "${BG_PIDS[@]}"; do
            if kill -0 $PID 2>/dev/null; then
                NEW_PIDS+=($PID)
            fi
        done
        BG_PIDS=("${NEW_PIDS[@]}")

        if [ ${#BG_PIDS[@]} -ge $PARALLEL_FILES ]; then
            sleep 2
        fi
    done

    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    OUTPUT_FILE="parsedData/AC_$(printf "%03d" $AC_NUM).json"

    # Check if already processed
    if [ -f "$OUTPUT_FILE" ]; then
        SIZE=$(stat -c%s "$OUTPUT_FILE" 2>/dev/null || echo "0")
        if [ $SIZE -gt 600 ]; then
            echo "✅ AC_${AC_NUM} already processed (${SIZE} bytes) - SKIPPING"
            SKIP_COUNT=$((SKIP_COUNT + 1))
            continue
        fi
    fi

    # Start processing in background
    echo "⚡ Starting AC_${AC_NUM} in background (${TOTAL_COUNT}/${END_AC})"
    (
        python gemini_vision_extractor_ultrafast.py $AC_NUM $MAX_WORKERS $DPI > "logs/ac_${AC_NUM}_ultrafast.log" 2>&1
        EXIT_CODE=$?

        if [ $EXIT_CODE -eq 0 ]; then
            SIZE=$(stat -c%s "$OUTPUT_FILE" 2>/dev/null || echo "0")
            if [ $SIZE -gt 600 ]; then
                echo "✅ AC_${AC_NUM} COMPLETED (${SIZE} bytes)"
            fi
        else
            echo "❌ AC_${AC_NUM} FAILED"
        fi
    ) &

    BG_PIDS+=($!)
done

# Wait for all remaining jobs
echo ""
echo "⏳ Waiting for final ${#BG_PIDS[@]} files to complete..."
for PID in "${BG_PIDS[@]}"; do
    wait $PID
done

# Final count
SUCCESS_COUNT=$(find parsedData -name "AC_*.json" -size +600c 2>/dev/null | wc -l)
FAIL_COUNT=$((TOTAL_COUNT - SUCCESS_COUNT - SKIP_COUNT))

echo ""
echo "================================================================"
echo "ULTRA-FAST BATCH PROCESSING COMPLETE"
echo "================================================================"
echo "Total: $TOTAL_COUNT"
echo "Successful: $SUCCESS_COUNT"
echo "Failed: $FAIL_COUNT"
echo "Skipped: $SKIP_COUNT"
echo "================================================================"

exit 0
