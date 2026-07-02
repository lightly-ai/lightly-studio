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

export interface Guardrail {
    name: string;
    required: boolean;
    /** True if it needs the PR API (CI only); false runs anywhere. */
    needsPrContext: boolean;
    run(context: GuardrailContext): Promise<GuardrailResult>;
}
