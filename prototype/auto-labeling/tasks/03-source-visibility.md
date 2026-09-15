# Source deletion and confidence visibility

Owner: source agent. Status: pending.

Read ../PROTOCOL.md, original UX spec, applicable frontend/Python/backend/best-practices/glossary skills and repository guidance.

Own annotation source row delete action and confirmation naming source/count; show source menu even with one source. Fix existing collection deletion for annotation sources, including annotation samples, dependent rows and coverage cleanup; preserve parent images. Own confidence slider beside source/class filters and confidence visibility in grid and details sidebar. Use a dedicated shared store/hook (not useGlobalStorage, root edits it). Null confidence stays visible. Slider hides annotations only; export retains all written annotations. Coordinate details image-container rendering with root: send hook import and use, do not edit that file. No tests. No new inference code.

Complete when any source can be deleted through confirmation, dependent data is cleaned up, queries refreshed, and confidence visibility affects grid and details consistently without pruning server data. Report checks and update this task's status.
