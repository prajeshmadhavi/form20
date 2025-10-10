#!/bin/bash

echo "=========================================="
echo "PROCESSING STATUS - 3 Remaining PDFs"
echo "=========================================="
echo ""

# Check running processes
RUNNING=$(ps aux | grep "gemini_vision_extractor.py" | grep -v grep | wc -l)
echo "🔄 Active Processes: $RUNNING"

if [ $RUNNING -gt 0 ]; then
    ps aux | grep "gemini_vision_extractor.py" | grep -v grep | while read -r line; do
        PID=$(echo "$line" | awk '{print $2}')
        AC=$(echo "$line" | awk '{print $NF}')
        ELAPSED=$(ps -p $PID -o etime= | tr -d ' ')
        echo "  • AC_$AC (PID: $PID, Running: $ELAPSED)"
    done
fi

echo ""
echo "📁 JSON Files Created:"
for ac in 39 113 234; do
    if [ -f "parsedData/AC_${ac}.json" ]; then
        SIZE=$(ls -lh "parsedData/AC_${ac}.json" | awk '{print $5}')
        echo "  ✅ AC_$ac - $SIZE"
    else
        echo "  ⏳ AC_$ac - Processing..."
    fi
done

echo ""
echo "=========================================="
echo "Run: watch -n 10 ./check_processing_status.sh"
echo "=========================================="
