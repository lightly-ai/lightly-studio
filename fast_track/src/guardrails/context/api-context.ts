import type { ChangedFile, GuardrailContext, Octokit } from './types';

/**
 * CI {@link GuardrailContext} backed by `pulls.listFiles`, mirroring the git
 * provider's `ChangedFile` shape (optional `patch`, omitted for binary/large
 * files). The Octokit client is injected, never constructed here, so this file
 * touches no credential and runs no `@actions/*` code.
 */
export class ApiGuardrailContext implements GuardrailContext {
    readonly baseRef: string;
    readonly octokit: Octokit;
    private readonly owner: string;
    private readonly repo: string;
    private readonly pullNumber: number;
    private cache?: Promise<ChangedFile[]>;

    constructor(options: ApiGuardrailContextOptions) {
        this.octokit = options.octokit;
        this.owner = options.owner;
        this.repo = options.repo;
        this.pullNumber = options.pullNumber;
        this.baseRef = options.baseRef;
    }

    async changedFiles(): Promise<ChangedFile[]> {
        // Memoize the promise: page the API once even across several guardrails
        // or concurrent callers.
        this.cache ??= this.fetchChangedFiles();
        return this.cache;
    }

    private async fetchChangedFiles(): Promise<ChangedFile[]> {
        const files: ChangedFile[] = [];
        // Stop on a short page (the last one); MAX_FILES guards the API's own cap.
        for (let page = 1; files.length < MAX_FILES; page++) {
            const { data } = await this.octokit.rest.pulls.listFiles({
                owner: this.owner,
                repo: this.repo,
                pull_number: this.pullNumber,
                per_page: PER_PAGE,
                page
            });
            for (const file of data) {
                files.push(toChangedFile(file));
            }
            if (data.length < PER_PAGE) break;
        }
        return files.slice(0, MAX_FILES);
    }
}

export interface ApiGuardrailContextOptions {
    octokit: Octokit;
    owner: string;
    repo: string;
    pullNumber: number;
    /** The PR's base ref (from the event) so stacked/non-main bases diff correctly. */
    baseRef: string;
}

/** `listFiles` returns at most 100 items per page. */
const PER_PAGE = 100;
/** GitHub's `pulls.listFiles` returns at most 3000 files for a PR. */
const MAX_FILES = 3000;

/** The subset of a `pulls.listFiles` item this provider reads. */
interface ApiChangedFile {
    filename: string;
    additions: number;
    deletions: number;
    patch?: string;
}

/** Map an API file entry to a {@link ChangedFile}, keeping `patch` only when present. */
export function toChangedFile(file: ApiChangedFile): ChangedFile {
    return {
        path: file.filename,
        additions: file.additions,
        deletions: file.deletions,
        ...(file.patch !== undefined ? { patch: file.patch } : {})
    };
}
