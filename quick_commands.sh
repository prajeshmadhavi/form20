#!/bin/bash
# Quick commands for batch processing management

case "$1" in
    status)
        echo "Quick Status Check:"
        python check_status.py
        ;;

    monitor)
        echo "Starting real-time monitor (Ctrl+C to exit)..."
        python monitor_batch_progress.py
        ;;

    logs)
        echo "Showing master log (Ctrl+C to exit)..."
        tail -f batch_processing_master.log
        ;;

    ac)
        if [ -z "$2" ]; then
            echo "Usage: ./quick_commands.sh ac <number>"
            echo "Example: ./quick_commands.sh ac 5"
        else
            AC_NUM=$2
            LOG_FILE="batch_logs/AC_${AC_NUM}_log.txt"
            if [ -f "$LOG_FILE" ]; then
                echo "Showing log for AC_$AC_NUM:"
                cat "$LOG_FILE"
            else
                echo "Log file not found: $LOG_FILE"
                echo "AC_$AC_NUM may not have been processed yet"
            fi
        fi
        ;;

    running)
        echo "Checking if batch process is running..."
        if ps aux | grep -v grep | grep -q batch_process_all_pdfs.py; then
            echo "✅ Batch process is RUNNING"
            ps aux | grep batch_process_all_pdfs.py | grep -v grep
        else
            echo "❌ Batch process is NOT running"
            echo "Start it with: ./run_batch_persistent.sh"
        fi
        ;;

    stop)
        echo "Stopping batch processing..."
        pkill -f batch_process_all_pdfs.py
        pkill -f run_batch_persistent.sh
        echo "Stopped. Progress is saved in batch_processing_tracking.json"
        ;;

    restart)
        echo "Restarting batch processing..."
        pkill -f batch_process_all_pdfs.py
        pkill -f run_batch_persistent.sh
        sleep 2
        nohup ./run_batch_persistent.sh > batch_main_output.log 2>&1 &
        echo "Restarted in background"
        sleep 3
        python check_status.py
        ;;

    dashboard)
        echo "Dashboard location:"
        echo "file://$(pwd)/dashboard_final.html"
        ;;

    completed)
        echo "Completed ACs:"
        python -c "import json; data=json.load(open('batch_processing_tracking.json')); print(sorted(data.get('completed', [])))"
        ;;

    failed)
        echo "Failed ACs:"
        python -c "import json; data=json.load(open('batch_processing_tracking.json')); print(data.get('failed', []))"
        ;;

    help|*)
        cat << 'EOF'
================================================================================
BATCH PROCESSING QUICK COMMANDS
================================================================================

Usage: ./quick_commands.sh <command> [arguments]

Commands:

  status          Quick status check
  monitor         Real-time progress monitor
  logs            View master log (live tail)
  ac <number>     View log for specific AC (e.g., ac 5)
  running         Check if process is running
  stop            Stop batch processing
  restart         Restart batch processing (resumes from where it stopped)
  dashboard       Show dashboard URL
  completed       List completed ACs
  failed          List failed ACs
  help            Show this help

Examples:

  ./quick_commands.sh status
  ./quick_commands.sh monitor
  ./quick_commands.sh ac 15
  ./quick_commands.sh running

================================================================================
EOF
        ;;
esac
