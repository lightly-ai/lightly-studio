import type { GuardrailResult } from '../../shared/verdict';

export interface ChangedFile {
    path: string;
    additions: number;
    deletions: number;
}

/**
 * Backed by git locally and the API in CI. Exposes the changed files (counts
 * only) plus the base ref they were measured against. The base ref is the
 * escape hatch: a guardrail that needs more than the counts — e.g. its own
 * diff hunks — can recover them from it, so no context has to precompute and
 * carry patch text that most guardrails never read.
 */
export interface GuardrailContext {
    /** The ref the change set is diffed against (three-dot, i.e. merge-base). */
    baseRef: string;
    changedFiles(): Promise<ChangedFile[]>;
}

/** A guardrail's `run` output; the runner adds the `name` from the definition. */
export type GuardrailOutcome = Omit<GuardrailResult, 'name'>;

export interface Guardrail {
    name: string;
    required: boolean;
    /** True if it needs the PR API (CI only); false runs anywhere. */
    needsPrContext: boolean;
    run(context: GuardrailContext): Promise<GuardrailOutcome>;
}
