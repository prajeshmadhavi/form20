#!/bin/bash
echo "=========================================="
echo "DETAILED PROGRESS REPORT"
echo "=========================================="
echo ""
echo "✅ SUCCESSFULLY COMPLETED (8):"
grep ",completed," failed_and_pending_acs.csv | cut -d',' -f1,2,3,7 | while IFS=, read -r ac name district remarks; do
    echo "  AC_$ac - $name ($district)"
    echo "    $remarks"
done
echo ""
echo "❌ FAILED - PDF NOT FOUND:"
grep "PDF not found" failed_and_pending_acs.csv | cut -d',' -f1,2,3 | while IFS=, read -r ac name district; do
    echo "  AC_$ac - $name ($district)"
done
echo ""
echo "⏳ CURRENTLY PROCESSING:"
tail -5 failed_reprocess_logs/reprocessing_log.txt | grep "PROCESSING AC_" || echo "  AC_71 - Chandrapur (SC)"
echo ""
echo "📊 SUMMARY:"
COMPLETED=$(grep -c ",completed," failed_and_pending_acs.csv)
PENDING=$(grep -c ",pending," failed_and_pending_acs.csv)
FAILED=$(grep -c ",failed," failed_and_pending_acs.csv)
TOTAL=54
echo "  Completed: $COMPLETED/54"
echo "  Failed: $FAILED/54"
echo "  Pending: $PENDING/54"
echo "  Success Rate: $(echo "scale=1; $COMPLETED * 100 / ($COMPLETED + $FAILED)" | bc)%"
echo "=========================================="
