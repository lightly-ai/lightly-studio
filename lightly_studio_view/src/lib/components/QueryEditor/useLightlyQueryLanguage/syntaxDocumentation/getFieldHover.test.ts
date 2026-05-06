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

describe('getFieldHover', () => {
    it('returns image-scope field hover at top level', async () => {
        const { getFieldHover } = await import('./getFieldHover');
        const model = makeSyntaxDocModel({
            text: 'width > 10',
            wordAtPosition: { word: 'width', startColumn: 1, endColumn: 6 },
            includeGetValue: true,
            includeGetOffsetAt: true
        });
        const hover = getFieldHover(model as never, { lineNumber: 1, column: 2 } as never);

        expect(hover).toEqual({
            contents: [
                { value: '```\nImage.width: int\n```' },
                { value: 'Image width in pixels.' }
            ],
            range: expect.objectContaining({
                startLineNumber: 1,
                startColumn: 1,
                endLineNumber: 1,
                endColumn: 6
            })
        });
    });

    it('returns object-detection field hover inside object_detection(...)', async () => {
        const { getFieldHover } = await import('./getFieldHover');
        const model = makeSyntaxDocModel({
            text: 'object_detection(label == "cat")',
            wordAtPosition: { word: 'label', startColumn: 18, endColumn: 23 },
            includeGetValue: true,
            includeGetOffsetAt: true
        });
        const hover = getFieldHover(model as never, { lineNumber: 1, column: 19 } as never);

        expect(hover).toEqual({
            contents: [
                { value: '```\nObjectDetection.label: string\n```' },
                { value: 'Class label of the detection.' }
            ],
            range: expect.objectContaining({
                startLineNumber: 1,
                startColumn: 18,
                endLineNumber: 1,
                endColumn: 23
            })
        });
    });

    it('returns null when no field documentation is available', async () => {
        const { getFieldHover } = await import('./getFieldHover');
        const model = makeSyntaxDocModel({
            text: 'unknown > 10',
            wordAtPosition: { word: 'unknown', startColumn: 1, endColumn: 8 },
            includeGetValue: true,
            includeGetOffsetAt: true
        });

        expect(getFieldHover(model as never, { lineNumber: 1, column: 2 } as never)).toBeNull();
    });
});
