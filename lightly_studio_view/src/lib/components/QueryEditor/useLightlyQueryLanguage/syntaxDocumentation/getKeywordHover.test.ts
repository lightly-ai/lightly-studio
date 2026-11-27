import { describe, expect, it, vi } from 'vitest';
import { makeSyntaxDocModel } from './testModel';

vi.mock('monaco-editor', () => ({
    Range: class Range {
        constructor(
            public startLineNumber: number,
            public startColumn: number,
            public endLineNumber: number,
            public endColumn: number
        ) {}
    }
}));

describe('getKeywordHover', () => {
    it('returns keyword hover for top-level keywords', async () => {
        const { getKeywordHover } = await import('./getKeywordHover');
        const model = makeSyntaxDocModel({
            text: 'width > 10 AND height < 20',
            wordAtPosition: { word: 'AND', startColumn: 12, endColumn: 15 },
            includeGetValueInRange: true
        });
        const hover = getKeywordHover(model as never, { lineNumber: 1, column: 13 } as never);

        expect(hover).toEqual({
            contents: [{ value: '**AND** — Boolean AND. Combines two conditions.' }],
            range: expect.objectContaining({
                startLineNumber: 1,
                startColumn: 12,
                endLineNumber: 1,
                endColumn: 15
            })
        });
    });

    it('returns keyword hover for `video:` when Monaco strips trailing colon', async () => {
        const { getKeywordHover } = await import('./getKeywordHover');
        const model = makeSyntaxDocModel({
            text: 'video: fps = 30',
            wordAtPosition: { word: 'video', startColumn: 1, endColumn: 6 },
            includeGetValueInRange: true
        });
        const hover = getKeywordHover(model as never, { lineNumber: 1, column: 3 } as never);

        expect(hover).toEqual({
            contents: [
                {
                    value: '**video:** — Switch the top-level scope from image to video. Must appear at the start of the query.'
                }
            ],
            range: expect.objectContaining({
                startLineNumber: 1,
                startColumn: 1,
                endLineNumber: 1,
                endColumn: 7
            })
        });
    });
    it.each(['', 'video: ', '(NOT '])(
        'explains metadata syntax and missing values in %s',
        async (prefix) => {
            const { getKeywordHover } = await import('./getKeywordHover');
            const startColumn = prefix.length + 1;
            const model = makeSyntaxDocModel({
                text: `${prefix}metadata["camera"] != "front"`,
                wordAtPosition: { word: 'metadata', startColumn, endColumn: startColumn + 8 },
                includeGetValue: true,
                includeGetOffsetAt: true,
                includeGetValueInRange: true
            });
            const hover = getKeywordHover(
                model as never,
                { lineNumber: 1, column: startColumn + 2 } as never
            );
            expect(hover?.contents).toEqual([
                {
                    value: expect.stringContaining(
                        'Missing paths, null, and values of another type do not match, including for `!=`'
                    )
                }
            ]);
            expect(hover?.contents).toEqual([
                {
                    value: expect.stringContaining(
                        '`NOT metadata["camera"] = "front"` also matches missing paths'
                    )
                }
            ]);
        }
    );

    it.each(['true', 'False'])(
        'documents boolean literal %s after metadata equality',
        async (word) => {
            const { getKeywordHover } = await import('./getKeywordHover');
            const prefix = 'metadata["reviewed"] = ';
            const startColumn = prefix.length + 1;
            const model = makeSyntaxDocModel({
                text: prefix + word,
                wordAtPosition: { word, startColumn, endColumn: startColumn + word.length },
                includeGetValue: true,
                includeGetOffsetAt: true,
                includeGetValueInRange: true
            });
            expect(
                getKeywordHover(model as never, { lineNumber: 1, column: startColumn } as never)
                    ?.contents
            ).toEqual([
                { value: expect.stringContaining('Use with `=` or `!=` on sample metadata.') }
            ]);
        }
    );

    it.each([
        ['classification(', 'metadata'],
        ['object_detection(', 'metadata'],
        ['segmentation_mask(', 'metadata'],
        ['file_name = "', 'metadata'],
        ['metadata["', 'metadata'],
        ['# ', 'metadata'],
        ['classification(metadata["reviewed"] = ', 'true'],
        ['metadata["score"] > ', 'true'],
        ['file_name = "', 'true']
    ])('does not advertise %s%s in unsupported positions', async (prefix, word) => {
        const { getKeywordHover } = await import('./getKeywordHover');
        const startColumn = prefix.length + 1;
        const model = makeSyntaxDocModel({
            text: prefix + word,
            wordAtPosition: { word, startColumn, endColumn: startColumn + word.length },
            includeGetValue: true,
            includeGetOffsetAt: true,
            includeGetValueInRange: true
        });
        expect(
            getKeywordHover(model as never, { lineNumber: 1, column: startColumn } as never)
        ).toBeNull();
    });
});
