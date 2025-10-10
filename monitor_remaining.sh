#!/bin/bash
echo "=========================================="
echo "REMAINING 2 PDFs PROCESSING MONITOR"
echo "=========================================="
echo ""

# Check if process is running
PID=$(pgrep -f "gemini_vision_extractor.py")
if [ -n "$PID" ]; then
    echo "🔄 Status: RUNNING"
    
    # Which AC is being processed
    AC_NUM=$(ps aux | grep "gemini_vision_extractor.py" | grep -v grep | awk '{print $NF}')
    echo "📄 Processing: AC_$AC_NUM"
    
    # Get process stats
    CPU=$(ps aux | grep $PID | grep -v grep | awk '{print $3}')
    MEM=$(ps aux | grep $PID | grep -v grep | awk '{print $4}')
    TIME=$(ps aux | grep $PID | grep -v grep | awk '{print $10}')
    
    echo "💻 CPU: ${CPU}%"
    echo "🧠 Memory: ${MEM}%"
    echo "⏱️  Runtime: $TIME"
else
    echo "⏸️  Status: STOPPED/COMPLETED"
fi

echo ""
echo "📁 Output Files:"
if [ -f "parsedData/AC_113.json" ]; then
    SIZE=$(ls -lh parsedData/AC_113.json | awk '{print $5}')
    echo "   ✅ AC_113.json ($SIZE)"
else
    echo "   ⏳ AC_113.json (pending)"
fi

if [ -f "parsedData/AC_234.json" ]; then
    SIZE=$(ls -lh parsedData/AC_234.json | awk '{print $5}')
    echo "   ✅ AC_234.json ($SIZE)"
else
    echo "   ⏳ AC_234.json (pending)"
fi

echo ""
echo "📋 Latest Log (last 10 lines):"
echo "=========================================="
tail -10 remaining_2_final.log 2>/dev/null || echo "No log output yet"
echo "=========================================="
