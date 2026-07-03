import type { ChangedFile, GuardrailContext, Octokit } from './types';

/** Identifies the PR whose files back the context. */
export interface PullRequestRef {
    owner: string;
    repo: string;
    pull_number: number;
}

/** The subset of a `pulls.listFiles` item this provider reads. */
export interface ApiFile {
    filename: string;
    additions: number;
    deletions: number;
    /** Omitted by the API for binary and very large files. */
    patch?: string;
}

/**
 * CI {@link GuardrailContext} backed by the GitHub API. The changed files come
 * from `pulls.listFiles`, which the API caps at ~3000 files (100 per page); a
 * PR larger than that is silently truncated at the ceiling — the git provider
 * never hits it, so the two providers diverge only on pathological PRs.
 *
 * `patch` is absent for binary/large files exactly as in the git provider, so
 * guardrails treat it as optional on either side.
 */
export class ApiGuardrailContext implements GuardrailContext {
    readonly baseRef: string;
    readonly octokit: Octokit;
    private readonly pr: PullRequestRef;
    private cache?: Promise<ChangedFile[]>;

    constructor(octokit: Octokit, pr: PullRequestRef, baseRef: string) {
        this.octokit = octokit;
        this.pr = pr;
        this.baseRef = baseRef;
    }

    changedFiles(): Promise<ChangedFile[]> {
        // The diff is fixed for one judgement; memoize (mirrors the git provider).
        this.cache ??= this.fetch();
        return this.cache;
    }

    private async fetch(): Promise<ChangedFile[]> {
        const files: ApiFile[] = await this.octokit.paginate(this.octokit.rest.pulls.listFiles, {
            owner: this.pr.owner,
            repo: this.pr.repo,
            pull_number: this.pr.pull_number,
            per_page: 100
        });
        return files.map(toChangedFile);
    }
}

/**
 * Map a `pulls.listFiles` item to a {@link ChangedFile}. Renamed `filename` is
 * already the new (b-side) path — matching the git provider's rename handling —
 * and `patch` is dropped when the API omits it, so the field is simply absent.
 */
export function toChangedFile(file: ApiFile): ChangedFile {
    return {
        path: file.filename,
        additions: file.additions,
        deletions: file.deletions,
        ...(file.patch !== undefined ? { patch: file.patch } : {})
    };
}
