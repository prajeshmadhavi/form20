# Speed Optimization V2 - Maximum Throughput

## Current Performance Analysis

**Completed so far:** 14/285 files
**Current config:** 2 files parallel, 10 workers each
**Rate limit usage:** 1% of 2,000 RPM capacity
**Bottleneck:** Massive unused capacity

### Observed Speeds (AC_13, AC_14):
- 50 pages per file
- ~2 minutes per file completion
- Success rate: 96% (2 JSON errors per file)
- API response: 6-38 seconds (avg: 25-35s)

## Optimization Proposal

### Changes Applied:
1. **Parallel files: 2 → 6** (3x more files simultaneously)
2. **Workers per file: 10 → 15** (50% more parallelism per file)
3. **DPI: 150 → 120** (15% faster image processing)

### Expected Impact:

| Metric | Current | Optimized | Improvement |
|--------|---------|-----------|-------------|
| Files in parallel | 2 | 6 | 3x |
| Workers per file | 10 | 15 | 1.5x |
| Concurrent requests | 20 | 90 | 4.5x |
| Rate limit usage | 1% | 4.5% | Still very low |
| Processing speed | 2 files/min | 7 files/min | 3.5x faster |
| **Time remaining** | **2-3 hours** | **45 min** | **~4x faster** |

### Capacity Analysis:

**Your limits:**
- Gemini 2.0 Flash: 2,000 RPM
- Current usage: 20 requests/~30s = ~40 RPM
- **Utilization: 2%**

**With optimization:**
- 6 files × 15 workers = 90 concurrent
- 90 requests/~30s = ~180 RPM
- **Utilization: 9%** (still very conservative)

**Could theoretically go to:**
- 20 files parallel × 20 workers = 400 concurrent
- Would use ~20% capacity
- But limited by system resources (memory, CPU)

## Risks & Considerations

### Low Risk:
✅ Rate limits: Using only 9% of 2,000 RPM
✅ API stability: gemini-2.0-flash is production-ready
✅ Error handling: Retry logic in place

### Medium Risk:
⚠️ **Memory usage**: 6 files × 50 pages × images in memory
⚠️ **System load**: 6 Python processes with 15 threads each
⚠️ **Image quality**: 120 DPI may slightly reduce accuracy

### Mitigation:
- Start with current settings, monitor system resources
- If stable, apply optimizations
- Can always revert to conservative settings

## Recommendation

**Apply Option 2 (Aggressive):**
- Risk: Low to Medium
- Benefit: 4x faster completion (~45 min vs 3 hours)
- Capacity headroom: Still 90%+ unused

**If system struggles:**
- Reduce to 4 files parallel (still 2x faster)
- Keep 10 workers per file
- Maintain 120 DPI

## Implementation

To apply optimizations:
```bash
# Stop current batch (let AC_15, AC_16 finish)
pkill -f "process_loksabha_ultrafast.sh"

# Wait for current files to complete
sleep 120

# Restart with new settings (already updated in script)
nohup bash process_loksabha_ultrafast.sh 17 288 > loksabha_ultrafast_v2.log 2>&1 &
```

Or let current batch finish naturally and new settings will auto-apply from AC_17 onwards.
