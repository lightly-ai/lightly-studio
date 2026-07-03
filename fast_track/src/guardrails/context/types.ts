import type { GuardrailResult } from '../../shared/verdict';

export interface ChangedFile {
    path: string;
    additions: number;
    deletions: number;
}

/**
 * Backed by git locally and the API in CI. Exposes changed-file counts plus the
 * base ref — the escape hatch for a guardrail that needs its own diff hunks, so
 * no context carries patch text most guardrails never read.
 */
export interface GuardrailContext {
    /** Ref the change set is diffed against (three-dot / merge-base). */
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
