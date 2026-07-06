import { DiffNameStatus, simpleGit } from 'simple-git';
import type { DiffResult } from 'simple-git';

import type { ChangedFile, FileStatus, GuardrailContext } from './types';

/**
 * Local {@link GuardrailContext} backed by `simple-git`. Diffs `baseRef...HEAD`
 * (three-dot, matching GitHub's Files-changed view). `diffSummary --name-status`
 * gives the status and destination path for each file in one call; line counts
 * are not provided by that format and default to 0.
 */
export class GitGuardrailContext implements GuardrailContext {
    readonly baseRef: string;
    private readonly git: ReturnType<typeof simpleGit>;
    private cache?: Promise<ChangedFile[]>;

    constructor(baseRef: string) {
        // An empty ref would make the range `...HEAD` — a valid but empty diff,
        // silently judging nothing. Reject it here rather than pass vacuously.
        const trimmed = baseRef.trim();
        if (trimmed === '') throw new Error('baseRef must not be empty');
        // Trimmed: a CI-supplied BASE_REF can carry stray whitespace.
        this.baseRef = trimmed;
        // color.ui=false: don't let a dev's `color.ui=always` colour parsed output.
        this.git = simpleGit({ config: ['color.ui=false'] });
    }

    /** Throw if the base ref does not resolve to a commit (e.g. a typo'd branch). */
    async assertBaseRefResolves(): Promise<void> {
        try {
            await this.git.revparse(['--verify', `${this.baseRef}^{commit}`]);
        } catch {
            throw new Error(`baseRef does not resolve to a commit: ${this.baseRef}`);
        }
    }

    async changedFiles(): Promise<ChangedFile[]> {
        // Memoize: the committed diff is fixed for one run, read by many guardrails.
        this.cache ??= (async () => {
            const summary = await this.git.diffSummary(['--name-status', `${this.baseRef}...HEAD`]);
            return summary.files.map(toChangedFile);
        })();
        return this.cache;
    }
}

/**
 * Map a `diffSummary --name-status` file entry to a {@link ChangedFile}.
 * For renames and copies `file` is already the destination path — no path
 * rewriting needed. Line counts default to 0 (not provided by `--name-status`).
 */
export function toChangedFile(file: DiffResult['files'][number]): ChangedFile {
    return {
        path: file.file,
        status: 'status' in file ? toFileStatus(file.status) : 'modified',
        additions: file.binary ? 0 : file.insertions,
        deletions: file.binary ? 0 : file.deletions
    };
}

function toFileStatus(status: DiffNameStatus | undefined): FileStatus {
    switch (status) {
        case DiffNameStatus.ADDED:
            return 'added';
        case DiffNameStatus.DELETED:
            return 'deleted';
        case DiffNameStatus.RENAMED:
            return 'renamed';
        case DiffNameStatus.COPIED:
            return 'copied';
        default:
            return 'modified';
    }
}
