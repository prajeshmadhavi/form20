# Form 20 PDF Data Extraction Implementation Plan

## System Overview
A robust, incremental data extraction system for processing 287 Form 20 PDFs with built-in progress tracking, quality control, and manual verification capabilities.

## Project Structure
```
form20/
├── IMPLEMENTATION_PLAN.md (this file)
├── EXTRACTION_RULES.md
├── scripts/
│   ├── main_extractor.py
│   ├── pdf_classifier.py
│   ├── standard_extractor.py
│   ├── devanagari_extractor.py
│   ├── ocr_extractor.py
│   ├── validator.py
│   ├── manual_verifier.py
│   └── progress_manager.py
├── config/
│   ├── extraction_config.json
│   ├── field_mappings.json
│   └── quality_thresholds.json
├── tracking/
│   ├── extraction_progress.json
│   ├── error_log.json
│   ├── quality_metrics.json
│   └── manual_corrections.json
├── output/
│   ├── extracted_data/
│   │   └── [constituency_wise_csvs]
│   ├── validation_reports/
│   └── consolidated_output.csv
└── backups/
    └── [timestamped_backups]
```

## Phase 1: Setup and Classification (Days 1-2)

### 1.1 PDF Classification System
**Purpose**: Automatically classify all 287 PDFs into extraction tiers

**Implementation**:
- Script: `pdf_classifier.py`
- Output: `tracking/pdf_classification.json`
- Classification criteria:
  - Tier 1: Standard English tabular (direct extraction)
  - Tier 2: Local language format (language processing needed)
  - Tier 3: Scanned/rotated (OCR required)

### 1.2 Progress Tracking System
**File**: `tracking/extraction_progress.json`
```json
{
  "total_pdfs": 287,
  "processed": 0,
  "pending": 287,
  "failed": 0,
  "manual_review": 0,
  "pdfs": {
    "AC_001": {
      "district": "Ahmednagar",
      "file_path": "VIDHANSABHA_2024/Ahmednagar/AC_001.pdf",
      "tier": 1,
      "status": "pending",
      "extraction_timestamp": null,
      "record_count": null,
      "quality_score": null,
      "manual_verified": false,
      "errors": []
    }
  }
}
```

## Phase 2: Tiered Extraction System (Days 3-7)

### 2.1 Main Extraction Controller
**Script**: `main_extractor.py`
**Features**:
- Resume capability from last processed PDF
- Automatic tier selection
- Error recovery
- Progress reporting every 10 PDFs

### 2.2 Tier-Specific Extractors

#### Tier 1: Standard Extractor
**Script**: `standard_extractor.py`
**Libraries**: pdfplumber, tabula-py
**Success Rate Target**: 95%

#### Tier 2: Devanagari Processor
**Script**: `devanagari_extractor.py`
**Libraries**: pdfplumber, indic-nlp-library
**Features**:
- Unicode text extraction
- Transliteration support
- Candidate name mapping

#### Tier 3: OCR Pipeline
**Script**: `ocr_extractor.py`
**Libraries**: pytesseract, pdf2image, opencv
**Features**:
- Image preprocessing (rotation, deskewing)
- OCR confidence scoring
- Multi-language support (English + Marathi)

## Phase 3: Quality Control Framework (Days 8-10)

### 3.1 Validation Rules
**File**: `config/quality_thresholds.json`
```json
{
  "min_records_per_pdf": 50,
  "max_records_per_pdf": 500,
  "required_fields_threshold": 0.9,
  "vote_total_variance_allowed": 1,
  "duplicate_check": true,
  "rules": {
    "constituency_number_format": "^AC_\\d{1,3}$",
    "vote_count_range": [0, 999999],
    "nota_mandatory": true,
    "total_validation": "sum(candidates) + nota + rejected = total"
  }
}
```

### 3.2 Validation Process
**Script**: `validator.py`
**Checks**:
1. Record count validation (user can specify expected range)
2. Mathematical consistency (vote totals)
3. Required fields completeness
4. Data type validation
5. Duplicate detection

### 3.3 Quality Metrics Dashboard
**File**: `tracking/quality_metrics.json`
```json
{
  "overall_quality_score": 0.0,
  "pdfs_processed": 0,
  "total_records_extracted": 0,
  "average_records_per_pdf": 0,
  "field_completeness": {},
  "validation_failures": [],
  "manual_corrections_made": 0
}
```

## Phase 4: Manual Verification Interface (Days 11-12)

### 4.1 Manual Review Tool
**Script**: `manual_verifier.py`
**Features**:
- Command-line interface for record count verification
- Side-by-side PDF viewer integration
- Quick correction capability
- Bulk approval for high-confidence extractions

### 4.2 User Commands
```bash
# Check specific PDF extraction
python manual_verifier.py --check AC_216

# Verify record count
python manual_verifier.py --verify-count AC_216 --expected 307

# Review all flagged PDFs
python manual_verifier.py --review-flagged

# Approve batch with high confidence
python manual_verifier.py --approve-batch --min-confidence 0.95
```

## Phase 5: Incremental Processing System (Days 13-15)

### 5.1 Batch Processing Strategy
- Process in batches of 10 PDFs
- Automatic checkpoint after each batch
- Resume capability from any point
- Parallel processing for Tier 1 PDFs (up to 4 threads)

### 5.2 Progress Monitoring
**Real-time Dashboard Output**:
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
✓ AC_143: 301 records (Q: 0.97)

Estimated Time Remaining: 2h 15m
====================================
```

## Phase 6: Error Handling and Recovery (Ongoing)

### 6.1 Error Categories
1. **Extraction Errors**: PDF corruption, unexpected format
2. **Validation Errors**: Data inconsistency, missing fields
3. **System Errors**: Memory issues, file access problems

### 6.2 Recovery Mechanisms
- Automatic retry with different extraction method
- Fallback to lower tier extractor
- Manual intervention queue
- Error logging with context

### 6.3 Error Log Structure
**File**: `tracking/error_log.json`
```json
{
  "errors": [
    {
      "pdf_id": "AC_183",
      "timestamp": "2024-01-15T10:30:00",
      "error_type": "extraction_failed",
      "tier_attempted": 1,
      "error_message": "Unable to extract tables",
      "retry_count": 2,
      "resolution": "pending_manual"
    }
  ]
}
```

## Phase 7: Alternative Data Sources (Days 16-17)

### 7.1 Gender Demographics
Since gender data is not in Form 20:
- Check for Form 21 (if available)
- Query Election Commission APIs
- Create placeholder fields for future updates

### 7.2 Data Enrichment
- Cross-reference with official election results
- Add constituency metadata
- Include district-level aggregations

## Execution Timeline

### Week 1
- Days 1-2: Setup and classification
- Days 3-7: Core extraction implementation

### Week 2
- Days 8-10: Quality control framework
- Days 11-12: Manual verification tools
- Days 13-15: Incremental processing

### Week 3
- Days 16-17: Alternative data sources
- Days 18-19: Full system testing
- Day 20: Production run begins

## Key Commands for Operation

```bash
# Initial setup and classification
python scripts/pdf_classifier.py --input VIDHANSABHA_2024/ --classify

# Start extraction (with resume capability)
python scripts/main_extractor.py --start --resume-from-last

# Check progress
python scripts/progress_manager.py --status

# Manual verification of specific PDF
python scripts/manual_verifier.py --pdf AC_216 --verify

# Validate all extracted data
python scripts/validator.py --validate-all

# Generate quality report
python scripts/validator.py --quality-report

# Export final consolidated CSV
python scripts/main_extractor.py --export-final
```

## Quality Assurance Checkpoints

### Before Processing
1. ✓ All PDFs classified correctly
2. ✓ Extraction rules configured
3. ✓ Test extraction on 5 sample PDFs

### During Processing
1. ✓ Monitor extraction rate (target: 15-20 PDFs/hour)
2. ✓ Check quality scores (threshold: >0.85)
3. ✓ Review error log every 50 PDFs

### After Processing
1. ✓ Validate total record count
2. ✓ Check field completeness (>90%)
3. ✓ Manual spot checks (5% random sample)
4. ✓ Mathematical validation of vote totals

## Success Metrics

| Metric | Target | Measurement |
|--------|---------|------------|
| PDF Processing Rate | 95%+ | Successful extractions / Total |
| Data Accuracy | 98%+ | Validated records / Total records |
| Field Completeness | 90%+ | Non-null fields / Expected fields |
| Manual Intervention | <10% | Manual reviews / Total PDFs |
| Processing Time | <24 hours | Total extraction time |

## Backup and Recovery

### Automatic Backups
- Progress state: Every 10 PDFs
- Extracted data: After each successful PDF
- Full system backup: Daily

### Recovery Procedures
1. System crash: Resume from last checkpoint
2. Corrupted extraction: Restore from backup, re-extract
3. Validation failure: Rollback to previous valid state

## Notes for Implementation

1. **Prioritize Tier 1 PDFs** for quick wins and validation
2. **Manual review queue** should be processed in parallel
3. **User can override** any automatic classification
4. **Keep raw extracted data** before any transformations
5. **Log everything** for audit trail and debugging

---
*This plan ensures systematic, trackable, and quality-controlled extraction of all 287 Form 20 PDFs with minimal data loss and maximum accuracy.*