import { DiffNameStatus } from 'simple-git';
import type { DiffResult } from 'simple-git';
import { describe, expect, it } from 'vitest';

import {
    GitGuardrailContext,
    parsePatchesByFile,
    renameTarget,
    toChangedFile
} from './git-context';

type DiffFiles = DiffResult['files'];

/** A name-status text-file entry as simple-git reports for `diffSummary --name-status`. */
function textFile(
    file: string,
    status: DiffNameStatus,
    insertions: number,
    deletions: number
): DiffFiles[number] {
    return {
        file,
        changes: insertions + deletions,
        insertions,
        deletions,
        binary: false,
        status,
        similarity: 0
    };
}

/** A binary diff entry: no line counts, byte sizes instead. */
function binaryFile(file: string): DiffFiles[number] {
    return { file, before: 0, after: 0, binary: true };
}

describe('toChangedFile', () => {
    it('maps M to modified', () => {
        expect(toChangedFile(textFile('src/foo.ts', DiffNameStatus.MODIFIED, 12, 3))).toEqual({
            path: 'src/foo.ts',
            status: 'modified',
            additions: 12,
            deletions: 3
        });
    });

    it('maps A to added', () => {
        expect(toChangedFile(textFile('src/new.ts', DiffNameStatus.ADDED, 5, 0))).toEqual({
            path: 'src/new.ts',
            status: 'added',
            additions: 5,
            deletions: 0
        });
    });

    it('maps D to deleted', () => {
        expect(toChangedFile(textFile('src/gone.ts', DiffNameStatus.DELETED, 0, 7))).toEqual({
            path: 'src/gone.ts',
            status: 'deleted',
            additions: 0,
            deletions: 7
        });
    });

    it('maps R to renamed using the destination path', () => {
        expect(
            toChangedFile({
                file: 'new/b.ts',
                changes: 2,
                insertions: 2,
                deletions: 0,
                binary: false,
                status: DiffNameStatus.RENAMED,
                from: 'old/a.ts',
                similarity: 100
            })
        ).toEqual({ path: 'new/b.ts', status: 'renamed', additions: 2, deletions: 0 });
    });

    it('maps C to copied using the destination path', () => {
        expect(
            toChangedFile({
                file: 'src/copy.ts',
                changes: 4,
                insertions: 4,
                deletions: 0,
                binary: false,
                status: DiffNameStatus.COPIED,
                from: 'src/orig.ts',
                similarity: 100
            })
        ).toEqual({ path: 'src/copy.ts', status: 'copied', additions: 4, deletions: 0 });
    });

    it('defaults to modified for other status letters (T, U, X, B)', () => {
        expect(toChangedFile(textFile('src/foo.ts', DiffNameStatus.CHANGED, 1, 2))).toEqual({
            path: 'src/foo.ts',
            status: 'modified',
            additions: 1,
            deletions: 2
        });
    });

    it('defaults to modified when no status is present', () => {
        expect(
            toChangedFile({
                file: 'src/foo.ts',
                changes: 8,
                insertions: 6,
                deletions: 2,
                binary: false,
                similarity: 0
            })
        ).toEqual({ path: 'src/foo.ts', status: 'modified', additions: 6, deletions: 2 });
    });

    it('normalises binary files to 0/0', () => {
        expect(toChangedFile(binaryFile('assets/logo.png'))).toEqual({
            path: 'assets/logo.png',
            status: 'modified',
            additions: 0,
            deletions: 0
        });
    });
});

describe('GitGuardrailContext', () => {
    it('rejects an empty base ref (would diff against nothing)', () => {
        expect(() => new GitGuardrailContext('')).toThrow(/must not be empty/);
        expect(() => new GitGuardrailContext('   ')).toThrow(/must not be empty/);
    });
});

describe('parsePatchesByFile', () => {
    it('returns an empty map for an empty diff', () => {
        expect(parsePatchesByFile('')).toEqual(new Map());
    });

    it('maps a single modified file to its full patch chunk', () => {
        const raw = [
            'diff --git a/src/foo.ts b/src/foo.ts',
            'index abc..def 100644',
            '--- a/src/foo.ts',
            '+++ b/src/foo.ts',
            '@@ -1,3 +1,4 @@',
            ' const x = 1;',
            '+const y = 2;'
        ].join('\n');

        expect(parsePatchesByFile(raw)).toEqual(
            new Map([
                [
                    'src/foo.ts',
                    [
                        'diff --git a/src/foo.ts b/src/foo.ts',
                        'index abc..def 100644',
                        '--- a/src/foo.ts',
                        '+++ b/src/foo.ts',
                        '@@ -1,3 +1,4 @@',
                        ' const x = 1;',
                        '+const y = 2;'
                    ].join('\n')
                ]
            ])
        );
    });

    it('maps multiple files to separate patch chunks', () => {
        const raw = [
            'diff --git a/a.ts b/a.ts',
            '--- a/a.ts',
            '+++ b/a.ts',
            '@@ -1 +1 @@',
            '+x',
            'diff --git a/b.ts b/b.ts',
            '--- a/b.ts',
            '+++ b/b.ts',
            '@@ -1 +1 @@',
            '+y'
        ].join('\n');

        expect(parsePatchesByFile(raw)).toEqual(
            new Map([
                [
                    'a.ts',
                    [
                        'diff --git a/a.ts b/a.ts',
                        '--- a/a.ts',
                        '+++ b/a.ts',
                        '@@ -1 +1 @@',
                        '+x',
                        ''
                    ].join('\n')
                ],
                [
                    'b.ts',
                    [
                        'diff --git a/b.ts b/b.ts',
                        '--- a/b.ts',
                        '+++ b/b.ts',
                        '@@ -1 +1 @@',
                        '+y'
                    ].join('\n')
                ]
            ])
        );
    });

    it('includes deleted files keyed by the source path (--- a/...)', () => {
        const raw = [
            'diff --git a/gone.ts b/gone.ts',
            '--- a/gone.ts',
            '+++ /dev/null',
            '@@ -1,2 +0,0 @@',
            '-line1',
            '-line2'
        ].join('\n');

        expect(parsePatchesByFile(raw)).toEqual(
            new Map([
                [
                    'gone.ts',
                    [
                        'diff --git a/gone.ts b/gone.ts',
                        '--- a/gone.ts',
                        '+++ /dev/null',
                        '@@ -1,2 +0,0 @@',
                        '-line1',
                        '-line2'
                    ].join('\n')
                ]
            ])
        );
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
