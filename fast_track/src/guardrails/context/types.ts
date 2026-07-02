import type { GuardrailResult } from '../../shared/verdict';

export interface ChangedFile {
    path: string;
    additions: number;
    deletions: number;
    /** Absent for large/binary files (the API omits it), so guardrails must tolerate that. */
    patch?: string;
}

/** Backed by git locally and the API in CI. */
export interface GuardrailContext {
    baseRef: string;
    changedFiles(): Promise<ChangedFile[]>;
}

/**
 * What a guardrail's `run` returns: a {@link GuardrailResult} minus its `name`.
 * The runner supplies the name from the definition, so a guardrail cannot
 * mislabel its own entry in the verdict — it isn't given the chance to.
 */
export type GuardrailOutcome = Omit<GuardrailResult, 'name'>;

export interface Guardrail {
    name: string;
    required: boolean;
    /** True if it needs the PR API (CI only); false runs anywhere. */
    needsPrContext: boolean;
    run(context: GuardrailContext): Promise<GuardrailOutcome>;
}
