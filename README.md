# Form 20 PDF Data Extraction System

A comprehensive system for extracting election data from 287 Form 20 PDFs across 36 districts in Maharashtra's VIDHANSABHA_2024 elections.

## System Overview

This system provides:
- **Automated PDF classification** into 3 tiers based on complexity
- **Tiered extraction** with appropriate methods for each PDF type
- **Progress tracking** with checkpoint and resume capabilities
- **Quality control** with validation and scoring
- **Manual verification** interface for corrections
- **Comprehensive reporting** at every stage

## Quick Start

### 1. Initialize the System
```bash
# Initialize tracking files
python scripts/progress_manager.py --init

# Check initial status
python scripts/progress_manager.py --status
```

### 2. Classify PDFs (Optional - auto-done during extraction)
```bash
python scripts/pdf_classifier.py --classify
```

### 3. Start Extraction
```bash
# Start fresh extraction
python scripts/main_extractor.py --start

# Resume from last checkpoint
python scripts/main_extractor.py --resume

# Start from specific PDF
python scripts/main_extractor.py --from-pdf AC_216
```

### 4. Monitor Progress
```bash
# Check current status
python scripts/progress_manager.py --status

# Detailed district-wise breakdown
python scripts/progress_manager.py --status --detailed
```

### 5. Manual Verification
```bash
# Interactive verification mode
python scripts/manual_verifier.py --interactive

# Check specific PDF
python scripts/manual_verifier.py --check AC_216

# Verify record count
python scripts/manual_verifier.py --verify-count AC_216:307

# Review all flagged PDFs
python scripts/manual_verifier.py --review-flagged

# Approve high-quality extractions in batch
python scripts/manual_verifier.py --approve-batch --min-confidence 0.95
```

## Directory Structure

```
form20/
├── README.md                    # This file
├── IMPLEMENTATION_PLAN.md       # Detailed implementation plan
├── EXTRACTION_RULES.md          # Extraction rules and standards
├── report.md                    # PDF parseability analysis
├── required_fields              # List of fields to extract
│
├── scripts/                     # Core extraction scripts
│   ├── main_extractor.py       # Main orchestrator
│   ├── progress_manager.py     # Progress tracking
│   ├── manual_verifier.py      # Manual verification interface
│   └── [extractors...]         # Tier-specific extractors
│
├── config/                      # Configuration files
│   ├── extraction_config.json  # Extraction settings
│   └── quality_thresholds.json # Validation thresholds
│
├── tracking/                    # Progress and logs
│   ├── extraction_progress.json # Main progress file
│   ├── quality_metrics.json    # Quality metrics
│   ├── error_log.json          # Error tracking
│   └── manual_corrections.json # Manual corrections log
│
├── output/                      # Extraction results
│   ├── extracted_data/         # Per-PDF extracted data
│   ├── validation_reports/     # Validation reports
│   └── consolidated_output.csv # Final consolidated data
│
└── VIDHANSABHA_2024/           # Source PDFs (287 files)
    └── [36 district folders]
```

## Key Features

### 1. Tiered Extraction System

**Tier 1 - Standard English Format (70% of PDFs)**
- Direct text extraction
- High success rate (95%+)
- Fast processing

**Tier 2 - Local Language Format (17% of PDFs)**
- Unicode/Devanagari support
- Transliteration capabilities
- Medium complexity

**Tier 3 - Scanned/Rotated Format (13% of PDFs)**
- OCR with preprocessing
- Image rotation correction
- Highest complexity

### 2. Progress Tracking

- **Automatic checkpoints** every 10 PDFs
- **Resume capability** from any point
- **Real-time dashboard** showing progress
- **Backup system** for recovery

### 3. Quality Control

- **Validation rules** for data consistency
- **Quality scoring** (0-1 scale)
- **Automatic flagging** for review
- **Mathematical verification** of vote totals

### 4. Manual Verification

- **Interactive interface** for corrections
- **Side-by-side PDF viewing** capability
- **Batch approval** for high-confidence results
- **Correction logging** for audit trail

## Common Operations

### Check Extraction Quality
```bash
# Generate quality report
python scripts/validator.py --quality-report

# Check specific PDF quality
python scripts/manual_verifier.py --check AC_216
```

### Handle Failures
```bash
# Reset failed PDF to retry
python scripts/progress_manager.py --reset AC_216

# Mark PDF as complete manually
python scripts/progress_manager.py --mark-complete AC_216:307:0.95
```

### Create Checkpoints
```bash
# Create named checkpoint
python scripts/progress_manager.py --checkpoint "after_district_pune"

# Automatic checkpoints created every 10 PDFs
```

### Export Results
```bash
# Export final consolidated CSV
python scripts/main_extractor.py --export-final

# Generate comprehensive report
python scripts/manual_verifier.py --report
```

## Monitoring Dashboard

During extraction, the system displays:
```
====================================
Form 20 Extraction Progress
====================================
Total PDFs: 287
Processed: 145 (50.5%)
Pending: 132
Failed: 8
Manual Review: 2

Current: AC_146 (Nagpur)
Tier: 1 (Standard)
Records Extracted: 298
Quality Score: 0.96

Recent Completions:
✓ AC_145: 312 records (Q: 0.98)
✓ AC_144: 289 records (Q: 0.94)

Estimated Time Remaining: 2h 15m
====================================
```

## Validation Rules

The system validates:
1. **Record count** within expected range
2. **Vote totals** mathematical consistency
3. **Required fields** presence
4. **Data types** correctness
5. **Duplicate detection** in polling stations

## Error Recovery

### Automatic Recovery
- Retry failed PDFs up to 3 times
- Fallback to lower tier extraction
- Checkpoint restoration on crash

### Manual Recovery
```bash
# Emergency stop
python scripts/main_extractor.py --emergency-stop

# Skip problematic PDF
python scripts/main_extractor.py --skip AC_123

# Force reprocess
python scripts/main_extractor.py --reprocess AC_123
```

## Performance Metrics

**Target Performance:**
- Processing Rate: 15-20 PDFs/hour
- Success Rate: 95%+
- Data Accuracy: 98%+
- Field Completeness: 90%+
- Manual Intervention: <10%

## Troubleshooting

### Common Issues

**1. Memory Issues**
```bash
# Reduce parallel processing
# Edit config/extraction_config.json
# Set "parallel_processing": {"tier_1": 2}
```

**2. OCR Failures**
```bash
# Check Tesseract installation
tesseract --version

# Install language packs
sudo apt-get install tesseract-ocr-mar  # Marathi
```

**3. Progress File Corruption**
```bash
# Restore from backup
cp backups/progress_checkpoint_latest.json tracking/extraction_progress.json
```

## Advanced Configuration

Edit `config/extraction_config.json`:
```json
{
  "max_retries": 3,
  "timeout_seconds": 300,
  "batch_size": 10,
  "quality_threshold": 0.85,
  "parallel_processing": {
    "tier_1": 4,
    "tier_2": 2,
    "tier_3": 1
  }
}
```

## System Requirements

- Python 3.8+
- 8GB RAM minimum (16GB recommended)
- 10GB free disk space
- PDF processing libraries (see requirements.txt)

## Support Files

- **IMPLEMENTATION_PLAN.md** - Detailed implementation phases
- **EXTRACTION_RULES.md** - Complete extraction ruleset
- **report.md** - Initial PDF analysis findings

## Notes

1. **Always run progress_manager.py --init** before first extraction
2. **Monitor error_log.json** for systematic issues
3. **Create checkpoints** before major operations
4. **Use manual verification** for critical data
5. **Keep backups** of tracking files

## Contact

For issues or questions, refer to the documentation files or check the error logs in the `tracking/` directory.

---
*System designed for incremental, quality-controlled extraction of Maharashtra election Form 20 data with comprehensive progress tracking and manual verification capabilities.*