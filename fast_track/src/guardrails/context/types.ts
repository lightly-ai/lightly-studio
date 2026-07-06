import type { GuardrailResult } from '../../shared/verdict';

export type FileStatus = 'added' | 'deleted' | 'modified' | 'renamed' | 'copied';

export interface ChangedFile {
    path: string;
    status: FileStatus;
    additions: number;
    deletions: number;
}

/** Backed by git locally and the API in CI. */
export interface GuardrailContext {
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
