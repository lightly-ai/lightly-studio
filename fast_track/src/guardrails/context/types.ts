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
    /** `local` runs from a plain checkout; `pr-only` needs the API and is skipped locally. */
    availability: 'local' | 'pr-only';
    run(context: GuardrailContext): Promise<GuardrailResult>;
}
