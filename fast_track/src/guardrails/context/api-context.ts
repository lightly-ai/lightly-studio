import type { ChangedFile, FileStatus, GuardrailContext, Octokit } from './types';

export type { Octokit };

/** `pulls.listFiles` caps per_page at 100. */
const PER_PAGE = 100;

/** The `pulls.listFiles` fields we read. `patch` is absent for binary / very large files. */
type ListedFile = {
    filename: string;
    status: string;
    additions: number;
    deletions: number;
    patch?: string;
};

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
    return {
        path: file.filename,
        status: toFileStatus(file.status),
        additions: file.additions,
        deletions: file.deletions,
        patch: file.patch
    };
}

/** GitHub's API uses 'removed' for deleted files; normalise to the shared FileStatus value. */
function toFileStatus(status: string): FileStatus {
    return status === 'removed' ? 'deleted' : (status as FileStatus);
}
