import type { GuardrailResult } from '../../shared/verdict';

export interface ChangedFile {
    path: string;
    additions: number;
    deletions: number;
}

/**
 * Backed by git locally and the API in CI. Exposes only the changed files;
 * how each provider decides what "changed" means (a base ref for git, the PR
 * event for the API) is a provider detail, not part of this contract.
 */
export interface GuardrailContext {
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
