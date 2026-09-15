# Backend inference

Owner: backend agent. Status: pending.

Read ../PROTOCOL.md, the original UX spec, Python/backend/best-practices/glossary skills and repository guidance.

Own new prototype annotation router and small supporting modules, app registration, and dependency declarations if needed. Implement discovery, HTTP client, mask conversion, filter-scoped batch persistence and stateless interactive inference. Follow the Studio API shapes in PROTOCOL.md so frontend work can proceed independently. Keep schema unchanged. Use existing file loading and resolver APIs. No new tests; run targeted static checks and report their outcome. Do not generate frontend API files (root will coordinate generation).

Complete when both modes use the backend with validated protocol data, batch writes isolated sources and accurate summary/coverage, and interactive only returns a preview. Report touched files, checks and limitations to root; update this task's status.
