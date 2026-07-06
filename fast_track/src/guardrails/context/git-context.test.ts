import { DiffNameStatus } from 'simple-git';
import { describe, expect, it } from 'vitest';

import { GitGuardrailContext, toChangedFile } from './git-context';

describe('toChangedFile', () => {
    it('maps M to modified', () => {
        expect(
            toChangedFile({
                file: 'src/foo.ts',
                changes: 0,
                insertions: 0,
                deletions: 0,
                binary: false,
                status: DiffNameStatus.MODIFIED,
                similarity: 0
            })
        ).toEqual({ path: 'src/foo.ts', status: 'modified', additions: 0, deletions: 0 });
    });

    it('maps A to added', () => {
        expect(
            toChangedFile({
                file: 'src/new.ts',
                changes: 0,
                insertions: 0,
                deletions: 0,
                binary: false,
                status: DiffNameStatus.ADDED,
                similarity: 0
            })
        ).toEqual({ path: 'src/new.ts', status: 'added', additions: 0, deletions: 0 });
    });

    it('maps D to deleted', () => {
        expect(
            toChangedFile({
                file: 'src/gone.ts',
                changes: 0,
                insertions: 0,
                deletions: 0,
                binary: false,
                status: DiffNameStatus.DELETED,
                similarity: 0
            })
        ).toEqual({ path: 'src/gone.ts', status: 'deleted', additions: 0, deletions: 0 });
    });

    it('maps R to renamed using the destination path', () => {
        expect(
            toChangedFile({
                file: 'new/b.ts',
                changes: 0,
                insertions: 0,
                deletions: 0,
                binary: false,
                status: DiffNameStatus.RENAMED,
                from: 'old/a.ts',
                similarity: 100
            })
        ).toEqual({ path: 'new/b.ts', status: 'renamed', additions: 0, deletions: 0 });
    });

    it('maps C to copied using the destination path', () => {
        expect(
            toChangedFile({
                file: 'src/copy.ts',
                changes: 0,
                insertions: 0,
                deletions: 0,
                binary: false,
                status: DiffNameStatus.COPIED,
                from: 'src/orig.ts',
                similarity: 100
            })
        ).toEqual({ path: 'src/copy.ts', status: 'copied', additions: 0, deletions: 0 });
    });

    it('defaults to modified for other status letters (T, U, X, B)', () => {
        expect(
            toChangedFile({
                file: 'src/foo.ts',
                changes: 0,
                insertions: 0,
                deletions: 0,
                binary: false,
                status: DiffNameStatus.CHANGED,
                similarity: 0
            })
        ).toEqual({ path: 'src/foo.ts', status: 'modified', additions: 0, deletions: 0 });
    });

    it('defaults to modified when no status is present', () => {
        expect(
            toChangedFile({
                file: 'src/foo.ts',
                changes: 0,
                insertions: 0,
                deletions: 0,
                binary: false,
                similarity: 0
            })
        ).toEqual({ path: 'src/foo.ts', status: 'modified', additions: 0, deletions: 0 });
    });

    it('normalises binary files to 0/0', () => {
        expect(
            toChangedFile({ file: 'assets/logo.png', before: 0, after: 0, binary: true })
        ).toEqual({ path: 'assets/logo.png', status: 'modified', additions: 0, deletions: 0 });
    });
});

describe('GitGuardrailContext', () => {
    it('rejects an empty base ref (would diff against nothing)', () => {
        expect(() => new GitGuardrailContext('')).toThrow(/must not be empty/);
        expect(() => new GitGuardrailContext('   ')).toThrow(/must not be empty/);
    });
});
