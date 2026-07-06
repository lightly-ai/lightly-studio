import type { GitHub } from '@actions/github/lib/utils';

import type { ChangedFile, GuardrailContext } from './types';

/**
 * A hydrated Octokit client, injected (never constructed here). Kept type-only so
 * the import erases at runtime and the local git path never loads `@actions/github`.
 */
export type Octokit = InstanceType<typeof GitHub>;

/** `pulls.listFiles` caps per_page at 100. */
const PER_PAGE = 100;

/** The `pulls.listFiles` fields we read — counts only, no patch. */
type ListedFile = { filename: string; additions: number; deletions: number };

export interface ApiGuardrailContextParams {
    octokit: Octokit;
    owner: string;
    repo: string;
    prNumber: number;
    baseRef: string;
}

/**
 * CI {@link GuardrailContext} backed by the GitHub API. `pulls.listFiles` is
 * paginated (the endpoint itself caps at ~3000 files) and each file maps to a
 * {@link ChangedFile} carrying counts only.
 */
export class ApiGuardrailContext implements GuardrailContext {
    readonly baseRef: string;
    readonly octokit: Octokit;
    private readonly owner: string;
    private readonly repo: string;
    private readonly prNumber: number;
    private cache?: Promise<ChangedFile[]>;

    constructor(params: ApiGuardrailContextParams) {
        // An empty base ref is a config error: a patch-fetching guardrail would
        // range against nothing. Reject it as the git provider does.
        if (params.baseRef.trim() === '') throw new Error('baseRef must not be empty');
        this.octokit = params.octokit;
        this.owner = params.owner;
        this.repo = params.repo;
        this.prNumber = params.prNumber;
        this.baseRef = params.baseRef;
    }

    async changedFiles(): Promise<ChangedFile[]> {
        // Memoize: the PR's file list is fixed for one run, read by many guardrails.
        this.cache ??= (async () => {
            const files = await this.octokit.paginate(this.octokit.rest.pulls.listFiles, {
                owner: this.owner,
                repo: this.repo,
                pull_number: this.prNumber,
                per_page: PER_PAGE
            });
            return files.map(toChangedFile);
        })();
        return this.cache;
    }
}

export function toChangedFile(file: ListedFile): ChangedFile {
    return { path: file.filename, additions: file.additions, deletions: file.deletions };
}
