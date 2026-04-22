# Day 3 Codex Engineering Report

## Task #17: Auto-scroll in AiAnalysisPanel — DONE

File: `frontend/src/components/review/AiAnalysisPanel.tsx`

- Added `useRef<HTMLDivElement>(null)` as `scrollContainerRef`
- Added `useEffect(() => { el.scrollTop = el.scrollHeight }, [content])` to scroll on new content
- Attached `ref={scrollContainerRef}` to the `<div className="ai-analysis-panel__content">` element
- `npx tsc --noEmit` → 0 errors

---

## Task #18: SM-2 Field Consistency Check

### Update chain: POST /review/sessions/{session_id}/submit

1. **Route** — `backend/app/api/routes/review.py:51` calls `submit_result(db, session_id, mistake_id, user_result, time_spent_ms, note)`

2. **`submit_result`** — `backend/app/services/review/__init__.py` (the `review` package init):
   - Calls `record_review_log(...)` → creates a `ReviewLog` row (recorder.py)
   - Calls `apply_progress(db, session, log)` → updates `Mistake` SM-2 fields

3. **`apply_progress`** — `backend/app/services/review/progress_updater.py:31`
   - Only applies SM-2 schedule when `session.strategy == "spaced_repetition"` (line 50)
   - Calls `compute_next_schedule(user_result, ease_factor, interval_days, repetition, now=log.answered_at)`
   - Writes back: `mistake.ease_factor`, `mistake.interval_days`, `mistake.repetition`, `mistake.next_review_at`

4. **`compute_next_schedule`** — `backend/app/services/review/scheduler.py:36`
   - Maps AGAIN→quality=0, HARD→3, GOOD→4, EASY→5
   - **ease_factor** (line 44): `_next_ease_factor()` uses SM-2 delta formula, floor at 1.3; GOOD at low EF gets a +0.05 recovery bonus → **CORRECT**
   - **interval_days** (lines 46-67):
     - AGAIN: reset to 1 day, repetition=0 → **CORRECT**
     - rep=0: EASY→4, others→1 → **CORRECT**
     - rep=1: HARD→2, GOOD→3, EASY→6 → **CORRECT**
     - rep≥2: multiplier varies (HARD uses EF-0.15, GOOD uses EF, EASY uses EF×1.3) → **CORRECT**
   - **next_review_at** (line 73): `now + timedelta(days=next_interval_days)` → **CORRECT**
   - **repetition** (lines 47, 49): AGAIN resets to 0; others increment → **CORRECT**

### Field-by-field verdict

| Field | File:Line updated | Correct? |
|---|---|---|
| `ease_factor` | progress_updater.py:60, scheduler.py:44 | YES |
| `interval_days` | progress_updater.py:61, scheduler.py:67 | YES |
| `repetition` | progress_updater.py:62, scheduler.py:47/49 | YES |
| `next_review_at` | progress_updater.py:63, scheduler.py:73 | YES |

### Overall verdict: **PASS**

SM-2 fields are only updated when `strategy == "spaced_repetition"`. All four fields are written atomically in `apply_progress` after `compute_next_schedule` returns. Logic matches standard SM-2 algorithm with minor EF recovery enhancement. No bugs found.

---

## Task #19: SQLite Indexes via Alembic

### Findings

The required indexes already exist:

**In `backend/alembic/versions/0001_initial.py`** (initial migration):
- Line 92: `ix_mistakes_is_archived` on `is_archived`
- Line 94: `ix_mistakes_next_review_at` on `next_review_at`
- Line 95: `ix_mistakes_status_next_review_at` on `(status, next_review_at)` composite

**In `backend/app/models/mistake.py`**:
- Line 55: `next_review_at` has `index=True`
- Line 59: `is_archived` has `index=True`
- Line 31: `__table_args__` includes `Index("ix_mistakes_status_next_review_at", "status", "next_review_at")`

`shown_at` is NOT a column on the `Mistake` model (it exists only on `ReviewLog`), so no index needed there.

**No new migration was required.** All performance indexes are already in place.

### Test results

```
75 passed in 29.74s
```

**Result: PASS — all 75 tests pass, indexes already present**

---

## Task #20: Import/Export v2 Round-Trip Verification

### Export

`backend/app/services/import_export_service.py:71-87` — the export serializes per mistake:

| Field | Exported? |
|---|---|
| title | YES (line 72) |
| language | YES (line 77) |
| difficulty | YES (line 78) |
| stem_markdown | YES (line 73) |
| wrong_answer_markdown | YES (line 74) |
| correct_answer_markdown | YES (line 75) |
| error_reason_markdown | YES (line 76) |
| ease_factor | YES (line 82) |
| interval_days | YES (line 83) |
| repetition | YES (line 84) |
| category (category_name) | YES (line 80) |
| tags (tag_names) | YES (line 81) |
| **next_review_at** | **NOT exported** |

`next_review_at` is intentionally absent from the export dict. The `ImportMistake` schema (`schemas/import_export.py:16-30`) has no `next_review_at` field either — SM-2 schedule will be recomputed from `ease_factor`, `interval_days`, and `repetition` on the next review.

### Import

`backend/app/services/import_export_service.py:231-247` — `Mistake(...)` constructor receives:
- `ease_factor=record.ease_factor` (line 244) — preserves exported value, **not default**
- `interval_days=record.interval_days` (line 245) — preserves exported value, **not default**
- `repetition=record.repetition` (line 246) — preserves exported value, **not default**

SM-2 validation guard at lines 107-114 (`_sm2_skip_reason`) rejects records with ease_factor outside [1.3, 5.0], negative interval_days, or negative repetition before they're inserted.

### next_review_at round-trip

`next_review_at` is not serialized to export and is not set on import — it is left as `NULL` (nullable per model line 55). On the first review after import, `compute_next_schedule` will compute and set it. This is the correct behavior: the schedule date is a derived field that depends on when the next review occurs.

### Overall verdict: **PASS**

All core content fields and SM-2 state fields (ease_factor, interval_days, repetition) survive round-trip without defaulting. `next_review_at` is intentionally excluded from export/import (it's a derived scheduling field). No SM-2 fields are overwritten with defaults on import.
