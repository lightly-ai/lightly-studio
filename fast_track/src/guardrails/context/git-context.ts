import { simpleGit } from 'simple-git';
import type { DiffResult } from 'simple-git';

import type { ChangedFile, GuardrailContext } from './types';

/**
 * Local {@link GuardrailContext} backed by `git` via `simple-git`. Diffs
 * `baseRef...HEAD` (three-dot: against the merge-base, matching GitHub's
 * Files-changed view) so a local run judges the same change set as Fast Track
 * Checks does in CI.
 *
 * `diffSummary` is numstat-accurate — it reports exact per-file add/delete
 * counts (not the scaled `--stat` bar) — which is all a guardrail needs. We
 * carry no patch text: the git and API providers both expose counts only, so
 * guardrails never see a diff hunk.
 */
export class GitGuardrailContext implements GuardrailContext {
    readonly baseRef: string;
    private readonly git: ReturnType<typeof simpleGit>;
    private cache?: Promise<ChangedFile[]>;

    constructor(baseRef: string) {
        this.baseRef = baseRef;
        // `color.ui=false` keeps a developer's `color.ui=always` from injecting
        // ANSI into the output simple-git parses. numstat is uncolored anyway,
        // so this is belt-and-suspenders, not load-bearing.
        this.git = simpleGit({ config: ['color.ui=false'] });
    }

    async changedFiles(): Promise<ChangedFile[]> {
        // Memoize: a run may consult the diff from several guardrails, but the
        // committed diff is fixed for the duration of one judgement. `async` so a
        // git failure surfaces as a rejected promise, not a synchronous throw.
        this.cache ??= (async () => {
            const summary = await this.git.diffSummary([`${this.baseRef}...HEAD`]);
            return toChangedFiles(summary.files);
        })();
        return this.cache;
    }
}

/**
 * Map a {@link DiffResult}'s files to {@link ChangedFile}s. Binary files carry
 * no line counts (simple-git reports `binary: true` with byte sizes instead),
 * so they normalise to 0/0. Rename entries name both sides; we keep the new
 * path so it lines up with the post-change tree.
 */
export function toChangedFiles(files: DiffResult['files']): ChangedFile[] {
    return files.map((file) => ({
        path: renameTarget(file.file),
        additions: file.binary ? 0 : file.insertions,
        deletions: file.binary ? 0 : file.deletions
    }));
}

/**
 * Resolve a diff path to its post-rename form. Git (and simple-git) write
 * renames two ways: `src/{old => new}/f.ts` (shared prefix/suffix) or
 * `old.ts => new.ts` (whole path). Both collapse to the new path; a plain path
 * is returned unchanged.
 */
export function renameTarget(rawPath: string): string {
    const braced = rawPath.replace(/\{.*? => (.*?)\}/g, '$1').replace(/\/{2,}/g, '/');
    if (braced !== rawPath) return braced;
    const arrow = rawPath.indexOf(' => ');
    return arrow === -1 ? rawPath : rawPath.slice(arrow + ' => '.length);
}
