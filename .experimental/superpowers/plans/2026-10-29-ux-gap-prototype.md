# UX gap prototype: implementation plan

Spec: the triage approved in chat on 2026-10-29, saved at
side-session-notes/local_e48937b7-3efd-461d-81aa-77679dfed784/ux-gap-prototype-triage.md, plus the
later answers: all gaps except few-shot/eval/query editor on annotations and metadata editing;
filter panel behaviour now, restyle from Gabriel's design later; box panel = class, source, delete;
step 0 rerun from S3; loader speed and hosted work last.

Agent rules shared by every gap: side-session-notes/.../ux-gap-agent-rules.md.
Execution: each gap is built by one background agent on its own branch `ux-gap/<name>` cut from
6d8579dac; this session cherry-picks the commits onto `claude/ux-gap-prototype-d56092`.

## Global constraints

- One commit per gap item; no CHANGELOG; no schema changes; no push, no PR.
- After every merge: backend static checks, frontend static checks, touched tests.

## Tasks

1. Merge ux-gap/sources (rows 20, 21, 22, 23).
2. Merge ux-gap/export (rows 37, 38, 39).
3. Merge ux-gap/filters (rows 29, 16, 36, 17, 30).
4. Merge ux-gap/gui-bugs (rows 26, 15, 19, 25, 11).
5. Merge ux-gap/tab-state (rows 27, 28).
6. Merge ux-gap/plot (rows 31, 13, 18, 33, 32).
7. Merge ux-gap/annotation-embeddings (row 34, LIG-11132).
8. Merge ux-gap/tile-fields (row 12).
9. Merge ux-gap/loaders (rows 6, 7, 9, 10, 1, 4).
10. Run tooling: `.experimental/ux-gap-prototype/run_caltech.sh`, local predictions import, rerun checklist.
11. Wave 2: loader speed (rows 8, 40) with an S3 benchmark.
12. Wave 2: hosted onboarding card (rows 2, 3, 5) in lightly-studio-self-hosted, local branch only.
13. Smoke test: build the prototype GUI, load Caltech, walk the checklist's GUI checks.
14. Final whole-branch review, one fix pass.
