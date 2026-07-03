import { execFileSync } from 'node:child_process';

import type { ChangedFile, GuardrailContext } from './types';

/**
 * Local {@link GuardrailContext} backed by `git`. Diffs `baseRef...HEAD`
 * (three-dot: against the merge-base, matching GitHub's Files-changed view) so
 * a local run judges the same change set as Fast Track Checks does in CI.
 *
 * Two commands, mirroring how the API separates counts from patch:
 * - `git diff --numstat` for per-file add/delete counts (binaries show as `-`),
 * - `git diff` for the patch text, split per file. Binary and rename-only files
 *   have no hunks, so their `patch` is absent — exactly like the API, which is
 *   why guardrails must tolerate a missing patch.
 */
export class GitGuardrailContext implements GuardrailContext {
    readonly baseRef: string;
    private cache?: Promise<ChangedFile[]>;

    constructor(baseRef: string) {
        this.baseRef = baseRef;
    }

    changedFiles(): Promise<ChangedFile[]> {
        // Memoize: a run may consult the diff from several guardrails, but the
        // committed diff is fixed for the duration of one judgement.
        this.cache ??= Promise.resolve(this.diff());
        return this.cache;
    }

    private diff(): ChangedFile[] {
        const range = `${this.baseRef}...HEAD`;
        const numstat = this.git(['diff', '--numstat', range]);
        const patchText = this.git(['diff', range]);
        return mergeChangedFiles(parseNumstat(numstat), splitPatches(patchText));
    }

    private git(args: string[]): string {
        // 256 MiB: large enough for any realistic PR diff; git resolves the repo
        // root itself, so the working directory doesn't matter.
        return execFileSync('git', args, { encoding: 'utf8', maxBuffer: 256 * 1024 * 1024 });
    }
}

interface NumstatEntry {
    path: string;
    additions: number;
    deletions: number;
}

/**
 * Parse `git diff --numstat` output: `<additions>\t<deletions>\t<path>` per
 * line. Binary files report `-` for both counts, which we normalise to 0.
 * Renames appear as `{old => new}` or `old => new` in the path; we keep the new
 * path so it lines up with the patch's b-side.
 */
export function parseNumstat(output: string): NumstatEntry[] {
    const entries: NumstatEntry[] = [];
    for (const line of output.split('\n')) {
        if (line.trim() === '') continue;
        const match = /^(-|\d+)\t(-|\d+)\t(.+)$/.exec(line);
        if (!match) continue;
        const [, additions, deletions, rawPath] = match;
        entries.push({
            path: renameTarget(rawPath!),
            additions: additions === '-' ? 0 : Number(additions),
            deletions: deletions === '-' ? 0 : Number(deletions)
        });
    }
    return entries;
}

/**
 * Resolve a numstat path to the post-rename path. Git writes renames two ways:
 * `src/{old => new}/f.ts` (shared prefix/suffix) or `old.ts => new.ts` (whole
 * path). Both collapse to the new path; a plain path is returned unchanged.
 */
function renameTarget(rawPath: string): string {
    const braced = rawPath.replace(/\{.*? => (.*?)\}/g, '$1').replace(/\/{2,}/g, '/');
    if (braced !== rawPath) return braced;
    const arrow = rawPath.indexOf(' => ');
    return arrow === -1 ? rawPath : rawPath.slice(arrow + ' => '.length);
}

/**
 * Split a full `git diff` into per-file patches keyed by the file's b-side
 * path. The stored patch is the hunk portion (from the first `@@` line), which
 * is what the API's `patch` field carries. Sections with no hunks — binary
 * files and pure renames — are omitted, so lookups for them miss and the
 * guardrail sees no patch.
 */
export function splitPatches(diff: string): Map<string, string> {
    const patches = new Map<string, string>();
    // Break before each `diff --git` header. The lookahead keeps the header
    // with its section; the leading '' (before the first header) is dropped.
    for (const section of diff.split(/^(?=diff --git )/m)) {
        if (!section.startsWith('diff --git ')) continue;
        const path = patchPath(section);
        const hunks = extractHunks(section);
        if (path !== undefined && hunks !== undefined) {
            patches.set(path, hunks);
        }
    }
    return patches;
}

/** The b-side path from a `diff --git a/<path> b/<path>` header line. */
function patchPath(section: string): string | undefined {
    const header = section.slice(0, section.indexOf('\n'));
    const match = /^diff --git a\/.+ b\/(.+)$/.exec(header);
    return match ? match[1] : undefined;
}

/** The patch body from the first `@@` hunk header onward, or undefined if none. */
function extractHunks(section: string): string | undefined {
    const match = /^@@ /m.exec(section);
    if (!match) return undefined;
    return section.slice(match.index).replace(/\n+$/, '');
}

/**
 * Join numstat entries (the authoritative file list + counts) with the patch
 * map. Numstat drives the result, so every changed file appears even when its
 * patch is absent.
 */
export function mergeChangedFiles(
    entries: NumstatEntry[],
    patches: Map<string, string>
): ChangedFile[] {
    return entries.map((entry) => {
        const patch = patches.get(entry.path);
        return {
            path: entry.path,
            additions: entry.additions,
            deletions: entry.deletions,
            ...(patch !== undefined ? { patch } : {})
        };
    });
}
