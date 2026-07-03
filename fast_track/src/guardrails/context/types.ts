import type { getOctokit } from '@actions/github';

import type { GuardrailResult } from '../../shared/verdict';

/** An authenticated Octokit, as returned by `@actions/github`'s `getOctokit`. */
export type Octokit = ReturnType<typeof getOctokit>;

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
    /**
     * The API client, present only under the API provider (CI). Local runs leave
     * it undefined — a `needsPrContext` guardrail may assume it, but a `local`
     * one must not, since it also runs from a plain checkout.
     */
    octokit?: Octokit;
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
