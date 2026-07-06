import { DiffNameStatus, simpleGit } from 'simple-git';
import type { DiffResult } from 'simple-git';

import type { ChangedFile, FileStatus, GuardrailContext } from './types';

/**
 * Local {@link GuardrailContext} backed by `simple-git`. Diffs `baseRef...HEAD`
 * (three-dot, matching GitHub's Files-changed view). Two parallel `diffSummary`
 * calls are made: `--name-status` for file status and destination paths, and the
 * default stat format for line counts. Results are merged by path.
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
            const range = `${this.baseRef}...HEAD`;
            const [nameStatus, stat] = await Promise.all([
                this.git.diffSummary(['--name-status', '-M', '-C', range]),
                this.git.diffSummary(['-M', '-C', range])
            ]);

            // name-status gives the correct destination path for renames/copies.
            const statusByPath = new Map(
                nameStatus.files.map((f) => [f.file, toChangedFile(f).status])
            );

            // stat gives line counts; renames use brace notation — resolve to destination.
            return stat.files.map((file) => {
                const path = renameTarget(file.file);
                return {
                    path,
                    status: statusByPath.get(path) ?? 'modified',
                    additions: file.binary ? 0 : file.insertions,
                    deletions: file.binary ? 0 : file.deletions
                };
            });
        })();
        return this.cache;
    }
}

/**
 * Map a `diffSummary --name-status` file entry to a {@link ChangedFile}.
 * For renames and copies `file` is already the destination path — no path
 * rewriting needed. Line counts default to 0; merge with a stat pass for
 * real counts (see {@link GitGuardrailContext.changedFiles}).
 */
export function toChangedFile(file: DiffResult['files'][number]): ChangedFile {
    return {
        path: file.file,
        status: 'status' in file ? toFileStatus(file.status) : 'modified',
        additions: file.binary ? 0 : file.insertions,
        deletions: file.binary ? 0 : file.deletions
    };
}

/**
 * Post-rename path. Git writes renames as `src/{old => new}/f.ts` (shared
 * prefix) or `old.ts => new.ts` (whole path); a plain path passes through.
 */
export function renameTarget(rawPath: string): string {
    const braced = rawPath.replace(/\{.*? => (.*?)\}/g, '$1').replace(/\/{2,}/g, '/');
    if (braced !== rawPath) return braced;
    const arrow = rawPath.indexOf(' => ');
    return arrow === -1 ? rawPath : rawPath.slice(arrow + ' => '.length);
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
