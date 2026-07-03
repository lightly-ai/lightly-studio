import { simpleGit } from 'simple-git';
import type { DiffResult } from 'simple-git';

import type { ChangedFile, GuardrailContext } from './types';

/**
 * Local {@link GuardrailContext} backed by `simple-git`. Diffs `baseRef...HEAD`
 * (three-dot, matching GitHub's Files-changed view). `diffSummary` gives exact
 * per-file line counts — all a guardrail needs; no patch text is carried.
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
            const summary = await this.git.diffSummary([`${this.baseRef}...HEAD`]);
            return toChangedFiles(summary.files);
        })();
        return this.cache;
    }
}

/**
 * Map `diffSummary` files to {@link ChangedFile}s. Binary files have no line
 * counts (simple-git reports byte sizes), so they become 0/0; renames keep the
 * new path.
 */
export function toChangedFiles(files: DiffResult['files']): ChangedFile[] {
    return files.map((file) => ({
        path: renameTarget(file.file),
        additions: file.binary ? 0 : file.insertions,
        deletions: file.binary ? 0 : file.deletions
    }));
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
