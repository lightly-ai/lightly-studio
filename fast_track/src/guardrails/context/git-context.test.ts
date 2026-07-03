import { describe, expect, it } from 'vitest';

import { mergeChangedFiles, parseNumstat, splitPatches } from './git-context';

describe('parseNumstat', () => {
    it('parses additions, deletions, and path per line', () => {
        const output = '12\t3\tsrc/foo.ts\n0\t7\tdocs/readme.md\n';
        expect(parseNumstat(output)).toEqual([
            { path: 'src/foo.ts', additions: 12, deletions: 3 },
            { path: 'docs/readme.md', additions: 0, deletions: 7 }
        ]);
    });

    it('normalises binary `-` counts to 0', () => {
        expect(parseNumstat('-\t-\tassets/logo.png\n')).toEqual([
            { path: 'assets/logo.png', additions: 0, deletions: 0 }
        ]);
    });

    it('resolves a braced rename to its new path', () => {
        expect(parseNumstat('2\t1\tsrc/{old => new}/bar.ts\n')).toEqual([
            { path: 'src/new/bar.ts', additions: 2, deletions: 1 }
        ]);
    });

    it('resolves a whole-path rename to its new path', () => {
        expect(parseNumstat('0\t0\told/a.ts => new/b.ts\n')).toEqual([
            { path: 'new/b.ts', additions: 0, deletions: 0 }
        ]);
    });

    it('ignores blank lines', () => {
        expect(parseNumstat('\n1\t0\ta.ts\n\n')).toEqual([
            { path: 'a.ts', additions: 1, deletions: 0 }
        ]);
    });
});

describe('splitPatches', () => {
    it('keys the hunk portion by the b-side path', () => {
        const diff = [
            'diff --git a/src/foo.ts b/src/foo.ts',
            'index abc1234..def5678 100644',
            '--- a/src/foo.ts',
            '+++ b/src/foo.ts',
            '@@ -1,2 +1,2 @@',
            ' context',
            '-old',
            '+new',
            ''
        ].join('\n');
        const patches = splitPatches(diff);
        expect(patches.get('src/foo.ts')).toBe('@@ -1,2 +1,2 @@\n context\n-old\n+new');
    });

    it('splits a multi-file diff', () => {
        const diff = [
            'diff --git a/a.ts b/a.ts',
            'index 111..222 100644',
            '--- a/a.ts',
            '+++ b/a.ts',
            '@@ -1 +1 @@',
            '-a',
            '+A',
            'diff --git a/b.ts b/b.ts',
            'index 333..444 100644',
            '--- a/b.ts',
            '+++ b/b.ts',
            '@@ -1 +1 @@',
            '-b',
            '+B',
            ''
        ].join('\n');
        const patches = splitPatches(diff);
        expect([...patches.keys()]).toEqual(['a.ts', 'b.ts']);
        expect(patches.get('a.ts')).toBe('@@ -1 +1 @@\n-a\n+A');
        expect(patches.get('b.ts')).toBe('@@ -1 +1 @@\n-b\n+B');
    });

    it('omits binary files (no hunks)', () => {
        const diff = [
            'diff --git a/logo.png b/logo.png',
            'index 111..222 100644',
            'Binary files a/logo.png and b/logo.png differ',
            ''
        ].join('\n');
        expect(splitPatches(diff).has('logo.png')).toBe(false);
    });

    it('returns an empty map for an empty diff', () => {
        expect(splitPatches('').size).toBe(0);
    });
});

describe('mergeChangedFiles', () => {
    it('attaches a patch when one exists for the path', () => {
        const entries = [{ path: 'a.ts', additions: 1, deletions: 1 }];
        const patches = new Map([['a.ts', '@@ hunk @@']]);
        expect(mergeChangedFiles(entries, patches)).toEqual([
            { path: 'a.ts', additions: 1, deletions: 1, patch: '@@ hunk @@' }
        ]);
    });

    it('omits the patch field entirely when absent (e.g. binary)', () => {
        const entries = [{ path: 'logo.png', additions: 0, deletions: 0 }];
        const result = mergeChangedFiles(entries, new Map());
        expect(result).toEqual([{ path: 'logo.png', additions: 0, deletions: 0 }]);
        expect('patch' in result[0]!).toBe(false);
    });

    it('lists every numstat file, patched or not', () => {
        const entries = [
            { path: 'a.ts', additions: 1, deletions: 0 },
            { path: 'logo.png', additions: 0, deletions: 0 }
        ];
        const patches = new Map([['a.ts', '@@ x @@']]);
        expect(mergeChangedFiles(entries, patches).map((f) => f.path)).toEqual([
            'a.ts',
            'logo.png'
        ]);
    });
});
