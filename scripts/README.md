# scripts/

One-off exploratory scripts from Step 1 (requirements + data audit). They were
used to profile `data/raw/` by hand — column blank rates, value counts,
duplicate detection, timestamp ordering — before any pipeline code existed.

They are **not** part of the shipped pipeline and nothing under `vireo/` or
`tests/` imports them. Findings they surfaced are written up properly in
`docs/data-audit.md` and `docs/decisions.md`. Kept for transparency (this is
what "audit the data first" actually looked like), not because they need to
run again — `python -m vireo.pipeline` supersedes all of them.

Run individually if useful: `python scripts/audit_01.py` (run from repo root).
