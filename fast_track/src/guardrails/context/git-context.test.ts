import type { DiffResult } from 'simple-git';
import { describe, expect, it } from 'vitest';

import { GitGuardrailContext, renameTarget, toChangedFiles } from './git-context';

type DiffFiles = DiffResult['files'];

/** A text-file diff entry as simple-git's `diffSummary` reports it. */
function textFile(file: string, insertions: number, deletions: number): DiffFiles[number] {
    return { file, changes: insertions + deletions, insertions, deletions, binary: false };
}

/** A binary diff entry: no line counts, byte sizes instead. */
function binaryFile(file: string): DiffFiles[number] {
    return { file, before: 0, after: 0, binary: true };
}

describe('toChangedFiles', () => {
    it('maps text files to their add/delete counts', () => {
        const files: DiffFiles = [textFile('src/foo.ts', 12, 3), textFile('docs/readme.md', 0, 7)];
        expect(toChangedFiles(files)).toEqual([
            { path: 'src/foo.ts', additions: 12, deletions: 3 },
            { path: 'docs/readme.md', additions: 0, deletions: 7 }
        ]);
    });

    it('normalises binary files to 0/0', () => {
        expect(toChangedFiles([binaryFile('assets/logo.png')])).toEqual([
            { path: 'assets/logo.png', additions: 0, deletions: 0 }
        ]);
    });

    it('keeps the new path for a braced rename', () => {
        expect(toChangedFiles([textFile('src/{old => new}/bar.ts', 2, 1)])).toEqual([
            { path: 'src/new/bar.ts', additions: 2, deletions: 1 }
        ]);
    });

    it('keeps the new path for a whole-path rename', () => {
        expect(toChangedFiles([textFile('old/a.ts => new/b.ts', 0, 0)])).toEqual([
            { path: 'new/b.ts', additions: 0, deletions: 0 }
        ]);
    });

    it('returns an empty list for no changes', () => {
        expect(toChangedFiles([])).toEqual([]);
    });
});

describe('GitGuardrailContext', () => {
    it('rejects an empty base ref (would diff against nothing)', () => {
        expect(() => new GitGuardrailContext('')).toThrow(/must not be empty/);
        expect(() => new GitGuardrailContext('   ')).toThrow(/must not be empty/);
    });
});

describe('renameTarget', () => {
    it('returns a plain path unchanged', () => {
        expect(renameTarget('src/foo.ts')).toBe('src/foo.ts');
    });

    it('resolves a braced rename with a shared prefix', () => {
        expect(renameTarget('src/{old => new}/bar.ts')).toBe('src/new/bar.ts');
    });

    it('resolves a whole-path rename', () => {
        expect(renameTarget('old/a.ts => new/b.ts')).toBe('new/b.ts');
    });
});
