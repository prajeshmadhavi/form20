# Form 20 PDF Extraction Rules and Standards

## Core Extraction Principles

### 1. Data Integrity Rules
- **Never skip a PDF** unless explicitly marked as corrupted
- **Always validate** mathematical relationships in vote counts
- **Preserve original data** before any transformations
- **Log every action** for audit trail

### 2. Field Extraction Priority
```
Priority 1 (MUST EXTRACT):
- Constituency Number
- Total Number of valid votes
- Elected Person Name
- Party Name Of Elected Person
- NOTA count

Priority 2 (SHOULD EXTRACT):
- All candidate names and vote counts
- Number of Rejected votes
- Total Number of Electors
- Serial Poll numbers

Priority 3 (EXTRACT IF AVAILABLE):
- Number Of Tender Votes
- Gender breakdown (if found in alternate sources)
```

## PDF Processing Rules

### Rule 1: PDF Classification
```python
if pdf.has_selectable_text() and pdf.language == "English":
    classify_as_tier_1()
elif pdf.has_selectable_text() and pdf.has_devanagari():
    classify_as_tier_2()
else:
    classify_as_tier_3()  # Requires OCR
```

### Rule 2: Extraction Attempts
- **Tier 1**: Try direct extraction first
- **Tier 2**: Try with Unicode support, fallback to Tier 3
- **Tier 3**: OCR with preprocessing
- **Maximum retries**: 3 per PDF
- **Timeout**: 5 minutes per PDF

### Rule 3: Record Count Validation
```python
expected_records = number_of_polling_stations
tolerance = 0.05  # 5% tolerance

if extracted_records < expected_records * (1 - tolerance):
    flag_for_manual_review("Too few records")
elif extracted_records > expected_records * (1 + tolerance):
    flag_for_manual_review("Too many records")
```

## Data Validation Rules

### Rule 4: Vote Total Consistency
```python
for each_polling_station:
    sum_candidate_votes = sum(all_candidate_votes)
    calculated_total = sum_candidate_votes + nota + rejected_votes

    if abs(calculated_total - reported_total) > 1:
        flag_validation_error("Vote totals don't match")
```

### Rule 5: Required Field Completeness
```python
required_fields = [
    'constituency_number',
    'total_valid_votes',
    'nota',
    'elected_person_name'
]

for field in required_fields:
    if field is None or field == "":
        mark_as_incomplete()
        request_manual_verification()
```

### Rule 6: Duplicate Detection
```python
# Check for duplicate polling station numbers
if len(polling_stations) != len(set(polling_stations)):
    flag_duplicate_error()

# Check for identical vote patterns (possible copy error)
if has_identical_vote_patterns():
    flag_for_review("Possible data duplication")
```

## Quality Scoring Rules

### Rule 7: Quality Score Calculation
```python
quality_score = (
    field_completeness * 0.4 +      # 40% weight
    validation_pass_rate * 0.3 +    # 30% weight
    extraction_confidence * 0.2 +    # 20% weight
    format_consistency * 0.1        # 10% weight
)

if quality_score < 0.85:
    require_manual_verification()
```

### Rule 8: Confidence Thresholds
| Extraction Method | Min Confidence | Action if Below |
|------------------|----------------|-----------------|
| Direct Text | 0.95 | Flag for review |
| Devanagari | 0.90 | Manual check names |
| OCR | 0.85 | Full manual verification |

## Error Handling Rules

### Rule 9: Error Recovery Strategy
```python
try:
    extract_with_primary_method()
except ExtractionError:
    try:
        extract_with_fallback_method()
    except:
        add_to_manual_queue()
        log_detailed_error()
```

### Rule 10: Critical Errors
**STOP processing if**:
- Memory usage > 80%
- Disk space < 1GB
- Network connectivity lost (if using APIs)
- More than 10 consecutive failures

## Manual Intervention Rules

### Rule 11: When to Request Manual Verification
1. Quality score < 0.85
2. Vote totals don't balance
3. Missing critical fields
4. OCR confidence < 0.85
5. Unusual patterns detected

### Rule 12: Manual Override Authority
User can:
- Override any automatic classification
- Correct any extracted value
- Mark PDF as unprocessable
- Approve batches despite low scores
- Set custom extraction parameters

## Progress Tracking Rules

### Rule 13: Checkpoint Creation
```python
create_checkpoint_when:
    - Every 10 PDFs processed
    - Before manual intervention
    - After error recovery
    - Every 30 minutes of processing
```

### Rule 14: Progress Reporting
```python
report_progress:
    - Real-time: Current PDF being processed
    - Every 10 PDFs: Summary statistics
    - On error: Detailed error context
    - On completion: Full extraction report
```

## Data Storage Rules

### Rule 15: File Naming Convention
```
Raw extraction: output/extracted_data/AC_[number]_raw.json
Validated data: output/extracted_data/AC_[number]_validated.csv
Error logs: tracking/errors/AC_[number]_errors.log
Manual corrections: tracking/manual/AC_[number]_corrections.json
```

### Rule 16: Backup Strategy
```python
backup_triggers = [
    "after_each_successful_extraction",
    "before_manual_corrections",
    "every_1_hour",
    "on_validation_completion"
]
```

## Special Cases

### Rule 17: Handling Edge Cases

#### Empty PDFs
```python
if pdf.page_count == 0 or pdf.text_length < 100:
    mark_as_empty()
    skip_with_log("PDF appears to be empty")
```

#### Corrupted PDFs
```python
if cannot_open_pdf():
    attempt_repair()
    if still_corrupted:
        mark_as_corrupted()
        notify_user()
```

#### Split Constituency Data
```python
if constituency_spans_multiple_pdfs:
    merge_extraction_results()
    validate_continuity()
```

## Performance Rules

### Rule 18: Resource Management
```python
max_parallel_tier1 = 4  # Can process 4 standard PDFs simultaneously
max_parallel_tier2 = 2  # Language processing is resource-intensive
max_parallel_tier3 = 1  # OCR requires full resources

if memory_usage > 70%:
    reduce_parallel_processing()
    force_garbage_collection()
```

### Rule 19: Optimization Triggers
```python
if extraction_time > 5_minutes:
    log_performance_issue()
    try_simplified_extraction()

if success_rate < 80%:
    review_extraction_parameters()
    suggest_rule_adjustments()
```

## Audit and Compliance

### Rule 20: Audit Trail Requirements
Every action must log:
1. Timestamp
2. PDF identifier
3. Action taken
4. Result/outcome
5. User/system initiator
6. Any errors or warnings

### Rule 21: Data Privacy
```python
# Never log sensitive information
sensitive_fields = []  # Define based on requirements

for field in sensitive_fields:
    mask_in_logs(field)
```

## Quality Assurance Protocols

### Rule 22: Sampling for Quality
```python
sample_size = max(20, total_pdfs * 0.05)  # 5% or minimum 20
random_sample = select_random(processed_pdfs, sample_size)

for pdf in random_sample:
    perform_detailed_quality_check()
    compare_with_source_pdf()
```

### Rule 23: Continuous Improvement
```python
if pattern_of_errors_detected():
    update_extraction_rules()
    reprocess_affected_pdfs()
    notify_user_of_improvements()
```

## User Interaction Rules

### Rule 24: User Notifications
**Notify user when**:
- Processing starts/completes
- Manual intervention needed
- Errors exceed threshold
- Unusual patterns detected
- Milestone reached (25%, 50%, 75%)

### Rule 25: User Controls
User can always:
```bash
# Pause processing
python main_extractor.py --pause

# Resume from checkpoint
python main_extractor.py --resume

# Skip problematic PDF
python main_extractor.py --skip AC_123

# Force reprocess
python main_extractor.py --reprocess AC_123

# Emergency stop
python main_extractor.py --emergency-stop
```

---
*These rules ensure consistent, reliable, and auditable extraction of Form 20 data while maintaining flexibility for manual intervention and quality control.*