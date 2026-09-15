# Batch auto-labeling UI

Owner: batch UI agent. Status: pending.

Read ../PROTOCOL.md, original UX spec, frontend/best-practices/glossary skills and repository guidance.

Own AutoLabelDialog components, useAutoLabelDialog, Header/Menu and MenuDialogHost integration. Implement image-only, filter-scoped entry; preflight model/endpoint readiness; free-text targets with class overrides (closed-set pick-list if advertised); required task choice, confidence floor, call multiplier, blocking execution state, unmatched-prompts-first summary, and closing summary navigates to image grid filtered to new source. Use TanStack Query and existing configured API client; handwritten local typed requests are acceptable until schema generation. Coordinate API mismatch with backend/root. No tests. Avoid editing global storage or details image container, owned by root.

Complete when the real UI covers config, loading/error, execution and summary/navigation. Run available static checks, report outcomes and update this task's status.
