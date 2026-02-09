# Architecture Documentation Organization

This document explains how architectural documentation is organized in this project.

## Structure

```
docs/
├── architecture/
│   ├── README.md                              # Index and overview
│   ├── ORGANIZATION.md                        # This file
│   └── api-refactoring-collection-hierarchy.md # Example proposal
└── coding-guidelines/
    ├── backend.md
    └── frontend.md
```

## Document Categories

### 1. Architecture Proposals

**Location:** `docs/architecture/`
**Purpose:** Design proposals for significant architectural changes
**Format:**
```markdown
# Title

**Status:** Proposed | Accepted | Rejected | Implemented
**Author:** Name/Team
**Date:** YYYY-MM-DD
**Related Issues:** #123, #456

## Executive Summary
Brief overview

## Current State
What exists today and what problems it has

## Proposed Solution
Detailed design of the new approach

## Benefits
Why this is better

## Implementation
How to build it

## Migration Path
How to transition from old to new
```

### 2. Coding Guidelines

**Location:** `docs/coding-guidelines/`
**Purpose:** Code style, patterns, and best practices
**Examples:**
- How to write backend code
- Frontend component patterns
- Testing standards

### 3. Root-Level Documents

**Location:** Project root
**Files:**
- `README.md` - Project overview and getting started
- `CONTRIBUTING.md` - How to contribute
- `CHANGELOG.md` - Version history
- `AGENTS.md` - AI agent configuration

## When to Create Each Type

### Create an Architecture Proposal when:
- Changing core system design
- Adding major new features
- Refactoring significant parts of the codebase
- Making decisions that affect multiple components
- Need team discussion and approval

### Create a Coding Guideline when:
- Establishing code patterns
- Documenting style preferences
- Sharing best practices
- Teaching how to write code in this project

### Update Root Documents when:
- Project description changes (README)
- Contributing process changes (CONTRIBUTING)
- New version released (CHANGELOG)

## Review Process

1. **Create proposal:** Write document in `docs/architecture/`
2. **Open PR:** Submit for review
3. **Discuss:** Team reviews and provides feedback
4. **Decide:** Accept, reject, or request changes
5. **Update status:** Mark as Accepted/Rejected
6. **Implement:** If accepted, build it
7. **Archive:** Mark as Implemented when done

## Best Practices

### For Proposals:
- ✅ Include concrete examples and code snippets
- ✅ Show both "before" and "after" states
- ✅ Explain the "why" not just the "what"
- ✅ Consider migration path and backwards compatibility
- ✅ Add diagrams if they help clarify
- ❌ Don't assume context - explain thoroughly
- ❌ Don't skip the "Current State" section

### For Organization:
- Keep proposals focused on one decision
- Use descriptive filenames
- Link to related issues and PRs
- Update the index in `README.md` when adding new docs

## Examples in the Wild

Projects with excellent architecture documentation:
- **Rust RFC Process:** https://github.com/rust-lang/rfcs
- **Python PEPs:** https://peps.python.org/
- **React RFCs:** https://github.com/reactjs/rfcs
- **Kubernetes KEPs:** https://github.com/kubernetes/enhancements/tree/master/keps
- **ADR Examples:** https://adr.github.io/
