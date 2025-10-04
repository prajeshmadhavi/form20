# CLAUDE.md

## Form 20 PDF Processing Rules - VISION-ONLY STRATEGY

### NEW STRATEGY (Updated October 2024)
**CRITICAL: ABANDON ALL OCR METHODS - USE ONLY VISION LLM**
• Use ONLY claude_vision_extractor.py for all PDF processing
• NO fallback to OCR, pdfplumber, or any text-based extraction
• Vision LLM provides superior accuracy and comprehensive data extraction
• Quality threshold: Files < 600 bytes or quality score < 60/100 marked as pending

### Environment Setup
• Always activate virtual environment: `source venv/bin/activate`
• Primary tool: claude_vision_extractor.py (Claude Vision API)
• Quality assessment: vision_quality_assessor.py
• Reprocessing: vision_only_reprocessor.py
• Use sudo password "Elixir#002" for system installations

### Processing Strategy
• **VISION FIRST AND ONLY**: Always use claude_vision_extractor.py
• Process one PDF at a time for optimal API usage
• No OCR fallback - if vision fails, mark as pending for manual review
• Quality assessment after each extraction
• Automatic reprocessing queue for low-quality outputs

### Quality Control Framework
• **File Size Check**: Outputs < 600 bytes marked as pending
• **Quality Score**: 0-100 scale, threshold 60/100 for acceptance
• **Quality Components**:
  - Constituency Number (20 points)
  - Total Electors (15 points)
  - Candidates List (25 points + 10 bonus for 5+ candidates)
  - Polling Station Details (20 points + 10 bonus for 10+ stations)
  - Elected Person (10 points)
  - Vision Method Bonus (5 points)

### Tracking System Enhancement
• **Status Values**: "completed", "pending", "failed"
• **Vision Assessment**: Added to tracking.json for each PDF
• **Automatic Updates**: Status updates based on file size and quality
• **Reprocessing Queue**: vision_reprocess_queue.json for pending files
• **Progress Monitoring**: Real-time dashboard updates

### Field Extraction Rules (Vision-Based)
• Constituency Number: Extract from PDF content and filename validation
• Total Electors: Vision extraction from document headers/tables
• Polling Station Data: Complete table extraction with candidate votes
• Candidate Information: Names, parties, vote counts, elected status
• Vote Totals: Valid votes, rejected votes, NOTA, tender votes
• Gender Breakdown: Male, female, others voting statistics

### File Organization
• Input: VIDHANSABHA_2024/[District]/AC_XXX.pdf
• Output: parsedData/AC_XXX.json (minimum 600 bytes)
• Quality Reports: vision_assessment_report.json
• Reprocess Queue: vision_reprocess_queue.json
• Progress Tracking: vision_reprocess_progress.json
• Logs: vision_only_reprocessing.log

### Error Handling & Recovery
• No OCR fallback - vision extraction only
• Failed extractions marked as "failed" status
• Automatic retry queue for low-quality outputs
• 15-minute timeout per PDF for vision processing
• Comprehensive logging of all failures and successes

### Commands for Vision-Only Processing
```bash
# Assess all existing JSON files for quality
python vision_quality_assessor.py --run

# Process Type 3 files using vision only (consolidated single script)
python type3_processor.py --start

# Process individual PDF with vision
python claude_vision_extractor.py [AC_NUMBER]
```

### Quality Metrics Targets
• Target: 90%+ files with quality score ≥ 60/100
• Target: 95%+ files with size ≥ 600 bytes
• Target: Complete candidate and polling station data
• Zero tolerance for OCR-based processing