# Frozen test set

- **Frozen:** 2026-10-04, before any system run on these questions.
- **Questions:** 53 (22 lookup, 5 multi-passage, 8 claim, 4 patent-number, 5 comparison,
  6 unanswerable, 3 legal) over the 16 patents in `../real_v1/corpus/`.
- **SHA-256 of dataset + corpus at freezing:** `06f8107e44dcd91551b4da07284abc6d6777de2510b6dce030b58315ad328972`
  (every result's `summary.json` → `dataset.sha256` shows which version it used).

Rules:
1. Never change the system because of results on this set. Tuning happens on `real_v1` (dev).
2. The team may **correct labels** (relevant passages, key facts, expected tools) after
   checking them with REVIEW.md. That changes the fingerprint; record each change in the
   item's `notes`, then re-score the stored runs (`make eval-rescore`) instead of
   re-running.
3. Questions are not edited or removed after results exist. If one is truly broken, keep
   it and explain in `notes`, or report results with and without it.
