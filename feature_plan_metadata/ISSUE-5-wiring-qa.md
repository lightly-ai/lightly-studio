# Issue 5 — End-to-end wiring pass & manual QA

**Depends on:** Issues 0–4. **Blocks:** none (final).

## Goal
Tie the features together, verify the shared pieces behave consistently, and do a manual
QA pass on real ~100k-sample data. This is a demo branch — favor a focused manual pass
over broad automated coverage.

## Tasks
- **Consistency:** confirm tag colors match across the embedding plot, distribution
  comparison series, and the GPS map.
- **Missing-value behavior** is consistent per the PRD across all features
  (balance = excluded influence; distribution = `(none)` bar/bin; coloring = gray).
- **Filter integration:** GPS rectangle-select and embedding select both update the shared
  active filter and reflect in the distribution panel and sample lists.
- **Gating:** GPS rail button appears only with `gps_coordinate` metadata; categorical
  balance form only lists categorical keys; numeric coloring only offered for numeric keys.
- **Performance sanity** at ~100k: distribution endpoint latency, GPS map render/pan,
  embedding recolor. Note anything visibly slow (don't optimize prematurely).
- **Static checks** on both sides so the branch stays runnable:
  - Backend: `cd lightly_studio && make static-checks`
  - Frontend: `cd lightly_studio_view && make static-checks`
- Add lightweight tests only where a bug is found or where a pure helper (binning,
  quantile edges, bbox test, priority coloring) is cheap to unit-test.

## Acceptance
- All four features work together on real data; static checks pass; no regression in the
  existing annotation balance / embedding-plot / distribution-panel flows.
