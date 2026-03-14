# Prompt Optimization Learnings

## What Works

- Explicit time range format "HH:MM-HH:MM" with rule for when to use it
- Price format rules: "$" prefix, ranges "$low-$high", "free" as string
- Price qualifier brevity: "kids free" not "kids 12 and under run free"
- Drop price descriptors: "per person", "all-inclusive", "each"
- Non-event detection (lost pet = all nulls)
- Organizer from sponsors/producers/message signers/instructors
- Year preference "prefer 2025" for ambiguous dates
- Relative dates → null (tmrw, this Fri, today)
- Hybrid location format ("Main Auditorium / Zoom")
- Flash sales/promotions classified as events, store as organizer
- Name: exclude org names, don't add words, don't append topics/subjects
- Location: preserve prepositions, drop trailing "location" word
- Few-shot examples (3 total) covering: price ranges, non-events, price brevity
- Daily schedule ranges valid even for multi-day events
- Multi-day event times (different days) → start time only
- "Discount %" and "by invitation only" are not prices → null

## What Doesn't Work

- Adding name/location rules without few-shot examples caused regression (exp 5: 97.50 vs 98.61)

## Failure Patterns

All resolved at 100% accuracy.
