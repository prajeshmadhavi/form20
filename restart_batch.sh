#!/bin/bash
# Restart/Resume batch processing script
# This ensures the batch process runs continuously until completion

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Activate virtual environment
source venv/bin/activate

# Log file for restart script
RESTART_LOG="batch_restart.log"

echo "======================================" | tee -a "$RESTART_LOG"
echo "Batch Processing Restart Script" | tee -a "$RESTART_LOG"
echo "Started at: $(date)" | tee -a "$RESTART_LOG"
echo "======================================" | tee -a "$RESTART_LOG"

# Run the batch processor
# It will automatically resume from where it left off
python -u batch_process_all_pdfs.py 2>&1 | tee -a batch_processing_output.log

EXIT_CODE=$?

echo "" | tee -a "$RESTART_LOG"
echo "======================================" | tee -a "$RESTART_LOG"
echo "Batch processing completed/stopped" | tee -a "$RESTART_LOG"
echo "Exit code: $EXIT_CODE" | tee -a "$RESTART_LOG"
echo "Ended at: $(date)" | tee -a "$RESTART_LOG"
echo "======================================" | tee -a "$RESTART_LOG"

# Check tracking file to see if we're done
if [ -f "batch_processing_tracking.json" ]; then
    COMPLETED=$(python -c "import json; data=json.load(open('batch_processing_tracking.json')); print(data.get('total_processed', 0))")
    FAILED=$(python -c "import json; data=json.load(open('batch_processing_tracking.json')); print(data.get('total_failed', 0))")
    SKIPPED=$(python -c "import json; data=json.load(open('batch_processing_tracking.json')); print(data.get('total_skipped', 0))")
    TOTAL=$((COMPLETED + FAILED + SKIPPED))

    echo "Progress: $COMPLETED completed, $FAILED failed, $SKIPPED skipped (Total: $TOTAL/288)" | tee -a "$RESTART_LOG"

    if [ "$TOTAL" -ge 288 ]; then
        echo "✅ All PDFs processed!" | tee -a "$RESTART_LOG"
    else
        echo "⚠️  Processing incomplete. Processed: $TOTAL/288" | tee -a "$RESTART_LOG"
    fi
fi

exit $EXIT_CODE
