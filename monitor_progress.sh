#!/bin/bash

# Progress monitor for LOKSABHA_2024 batch processing

echo "================================================================"
echo "LOKSABHA_2024 PROCESSING PROGRESS MONITOR"
echo "================================================================"
echo ""

# Count completed JSONs
COMPLETED=$(find parsedData -name "AC_*.json" -size +600c 2>/dev/null | wc -l)
echo "✅ Completed files: $COMPLETED / 285"

# Check currently processing
CURRENT_PYTHON=$(ps aux | grep "gemini_vision_extractor_optimized.py" | grep -v grep | awk '{print $13}')
if [ ! -z "$CURRENT_PYTHON" ]; then
    echo "🔄 Currently processing: AC_$CURRENT_PYTHON"
else
    echo "⏸️  No active processing"
fi

# Show recent completions
echo ""
echo "Recent completions (last 10):"
ls -lth parsedData/AC_*.json 2>/dev/null | head -10 | awk '{printf "  %s - %s\n", $9, $5}'

# Estimated time remaining
if [ $COMPLETED -gt 0 ]; then
    # Average 8 minutes per file (conservative estimate)
    REMAINING=$((285 - COMPLETED))
    EST_MINUTES=$((REMAINING * 8))
    EST_HOURS=$((EST_MINUTES / 60))
    echo ""
    echo "📊 Estimated time remaining: ~${EST_HOURS} hours ($REMAINING files remaining)"
fi

echo ""
echo "================================================================"

# Show batch log tail
echo ""
echo "Last 20 lines of batch log:"
echo "---"
tail -20 loksabha_batch_processing.log 2>/dev/null || echo "No log file yet"
