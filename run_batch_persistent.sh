#!/bin/bash
# Persistent batch runner - keeps running until all 288 PDFs are processed
# Automatically restarts on failure

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Maximum number of restart attempts
MAX_RESTARTS=10
RESTART_COUNT=0

echo "========================================="
echo "PERSISTENT BATCH PROCESSOR"
echo "========================================="
echo "This script will run until all 288 PDFs"
echo "are processed, automatically restarting"
echo "on failures."
echo ""
echo "To monitor progress in another terminal:"
echo "  python monitor_batch_progress.py"
echo ""
echo "To stop processing, press Ctrl+C"
echo "========================================="
echo ""

while [ $RESTART_COUNT -lt $MAX_RESTARTS ]; do
    echo "[$(date)] Starting batch processing (Attempt $((RESTART_COUNT + 1))/$MAX_RESTARTS)..."

    # Run the batch script
    ./restart_batch.sh

    EXIT_CODE=$?

    # Check if processing is complete
    if [ -f "batch_processing_tracking.json" ]; then
        TOTAL=$(python -c "import json; data=json.load(open('batch_processing_tracking.json')); print(data.get('total_processed', 0) + data.get('total_failed', 0) + data.get('total_skipped', 0))" 2>/dev/null)

        if [ "$TOTAL" -ge 288 ]; then
            echo ""
            echo "========================================="
            echo "✅ ALL 288 PDFs PROCESSED!"
            echo "========================================="
            echo "Check batch_processing_tracking.json for details"
            echo "Individual logs in batch_logs/ directory"
            exit 0
        fi
    fi

    # If exit code was 0 but not all processed, or if interrupted
    if [ $EXIT_CODE -eq 0 ] || [ $EXIT_CODE -eq 1 ]; then
        echo "[$(date)] Process stopped. Checking if resumable..."
        sleep 5
    else
        echo "[$(date)] Process failed with exit code $EXIT_CODE"
        RESTART_COUNT=$((RESTART_COUNT + 1))

        if [ $RESTART_COUNT -lt $MAX_RESTARTS ]; then
            echo "[$(date)] Restarting in 10 seconds..."
            sleep 10
        fi
    fi
done

echo ""
echo "========================================="
echo "⚠️  Maximum restart attempts reached"
echo "========================================="
echo "Please check logs for errors:"
echo "  - batch_processing_master.log"
echo "  - batch_logs/AC_*_log.txt"
exit 1
