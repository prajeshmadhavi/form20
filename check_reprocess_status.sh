#!/bin/bash

echo "=================================================="
echo "FAILED PDF REPROCESSING - LIVE STATUS"
echo "=================================================="
echo ""

# Check if process is running
PID=$(pgrep -f "failed_pdf_reprocessor.py")
if [ -n "$PID" ]; then
    echo "🔄 Status: RUNNING (PID: $PID)"
    # Get process runtime
    RUNTIME=$(ps -p $PID -o etime= | tr -d ' ')
    echo "⏱️  Runtime: $RUNTIME"
else
    echo "⏸️  Status: STOPPED"
fi

echo ""
echo "📊 PROGRESS:"
echo "=================================================="

# Count statuses from CSV
COMPLETED=$(grep -c ",completed," failed_and_pending_acs.csv 2>/dev/null || echo "0")
PENDING=$(grep -c ",pending," failed_and_pending_acs.csv 2>/dev/null || echo "0")
FAILED=$(grep -c ",failed," failed_and_pending_acs.csv 2>/dev/null || echo "0")
TOTAL=$((COMPLETED + PENDING + FAILED))

if [ $TOTAL -gt 0 ]; then
    PCT=$(echo "scale=1; $COMPLETED * 100 / $TOTAL" | bc)
else
    PCT=0
fi

echo "✅ Completed: $COMPLETED / $TOTAL ($PCT%)"
echo "⏳ Pending:   $PENDING"
echo "❌ Failed:    $FAILED"

echo ""
echo "🎯 RECENTLY COMPLETED:"
echo "=================================================="
grep ",completed," failed_and_pending_acs.csv | tail -5 | while IFS=, read -r ac_num name district status path proc_status remarks; do
    echo "  AC_$ac_num - $name: $remarks"
done

echo ""
echo "📋 CURRENT ACTIVITY (Last 5 log lines):"
echo "=================================================="
tail -5 failed_reprocess_logs/reprocessing_log.txt 2>/dev/null

echo ""
echo "=================================================="
echo "Run: watch -n 30 ./check_reprocess_status.sh"
echo "=================================================="
