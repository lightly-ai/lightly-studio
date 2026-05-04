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
            text: 'video: fps == 30',
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
});
