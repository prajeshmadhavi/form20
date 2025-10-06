# Batch Processing for All 288 PDFs

Comprehensive batch processing system for extracting data from all 288 Form 20 PDFs using Gemini Vision LLM.

## Features

✅ **Sequential Processing**: Processes AC_1 to AC_288 in order
✅ **Automatic Resume**: Continues from where it left off if interrupted
✅ **Comprehensive Logging**: Separate log file for each PDF
✅ **Progress Tracking**: JSON-based tracking with statistics
✅ **Error Handling**: Logs failures but continues processing
✅ **Persistent Execution**: Automatic restarts on crashes

## Files Created

### Main Scripts
- `batch_process_all_pdfs.py` - Main batch processor
- `gemini_vision_extractor.py` - Single PDF processor (already exists)
- `run_batch_persistent.sh` - Persistent runner with auto-restart
- `restart_batch.sh` - Manual restart script
- `monitor_batch_progress.py` - Real-time progress monitor
- `check_status.py` - Quick status checker

### Output Files
- `batch_processing_tracking.json` - Progress tracking data
- `batch_processing_master.log` - Master log file
- `batch_logs/AC_*_log.txt` - Individual log per PDF (288 files)
- `parsedData/AC_*.json` - Extracted data (288 files)

## Usage

### Start Batch Processing

```bash
# Option 1: Persistent mode (recommended - auto-restarts on failure)
./run_batch_persistent.sh

# Option 2: Single run (manual restart needed)
python batch_process_all_pdfs.py
```

### Monitor Progress

```bash
# Option 1: Real-time monitor (updates every 10 seconds)
python monitor_batch_progress.py

# Option 2: Quick status check
python check_status.py

# Option 3: View master log
tail -f batch_processing_master.log

# Option 4: View specific AC log
tail -f batch_logs/AC_5_log.txt
```

### Resume After Interruption

The system automatically resumes from where it stopped:

```bash
# Just run again - it will resume automatically
./run_batch_persistent.sh
```

### Check Individual PDF Log

```bash
cat batch_logs/AC_1_log.txt
```

## Tracking File Structure

`batch_processing_tracking.json` contains:

```json
{
  "start_time": "2025-10-06T07:00:00",
  "current_ac": 15,
  "in_progress": 15,
  "completed": [1, 2, 3, 4, ...],
  "failed": [7, 12],
  "skipped": [100, 101],
  "total_processed": 150,
  "total_failed": 2,
  "total_skipped": 5,
  "statistics": {
    "total_polling_stations": 52000,
    "total_api_calls": 2250,
    "total_processing_time": 45000
  }
}
```

## Processing Flow

1. **Check PDF exists** → Skip if not found
2. **Process PDF** → Call Gemini Vision API for each page
3. **Save results** → `parsedData/AC_X.json`
4. **Log details** → `batch_logs/AC_X_log.txt`
5. **Update tracking** → `batch_processing_tracking.json`
6. **Move to next** → AC_X+1

## Error Handling

- **PDF not found**: Logged as "skipped", continues to next
- **Processing fails**: Logged as "failed", continues to next
- **Exception occurs**: Logged with full traceback, continues to next
- **Script crash**: Auto-restart in persistent mode

## Estimated Time

- **Per PDF**: ~15-20 minutes (15 pages × ~60 sec/page)
- **Total for 288 PDFs**: ~72-96 hours (3-4 days)
- **Recommended**: Run in background using `nohup` or `screen`

## Run in Background

### Using nohup

```bash
nohup ./run_batch_persistent.sh > batch_output.log 2>&1 &
```

### Using screen

```bash
screen -S batch_processing
./run_batch_persistent.sh
# Press Ctrl+A then D to detach
# screen -r batch_processing  # to reattach
```

### Using tmux

```bash
tmux new -s batch_processing
./run_batch_persistent.sh
# Press Ctrl+B then D to detach
# tmux attach -t batch_processing  # to reattach
```

## Dashboard Integration

All output files are saved to `parsedData/AC_X.json` which is directly compatible with:

```
file:///home/prajesh/test/chandrakant/form20/dashboard_final.html
```

The dashboard will automatically display all processed PDFs.

## Troubleshooting

### Check if running

```bash
ps aux | grep batch_process
```

### Kill if needed

```bash
pkill -f batch_process_all_pdfs.py
```

### Check failed ACs

```bash
python -c "import json; data=json.load(open('batch_processing_tracking.json')); print('Failed:', data.get('failed', []))"
```

### Reprocess specific AC manually

```bash
source venv/bin/activate
python gemini_vision_extractor.py 5
```

## API Rate Limits

- 3 second delay between PDFs
- 2 second delay between pages
- Adjust in scripts if needed for rate limiting

## Storage Requirements

- **Vision Pages**: ~120MB per PDF × 288 = ~35GB
- **Output JSON**: ~100KB per PDF × 288 = ~30MB
- **Logs**: ~50KB per PDF × 288 = ~15MB
- **Total**: ~35GB

## Quality Assurance

Each processed PDF includes metadata:
- `extraction_method`: "gemini_vision_llm"
- `api_model`: "gemini-2.5-pro"
- `pages_processed`: number of pages
- `pages_available`: total pages in PDF

## Support

For issues:
1. Check `batch_processing_master.log`
2. Check specific AC log in `batch_logs/`
3. Check `batch_processing_tracking.json` for status
4. Run `python check_status.py` for overview
