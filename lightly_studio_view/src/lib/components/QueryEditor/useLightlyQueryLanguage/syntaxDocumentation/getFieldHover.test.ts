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
            text: 'object_detection(class_name = "cat")',
            wordAtPosition: { word: 'class_name', startColumn: 18, endColumn: 28 },
            includeGetValue: true,
            includeGetOffsetAt: true
        });
        const hover = getFieldHover(model as never, { lineNumber: 1, column: 19 } as never);

        expect(hover).toEqual({
            contents: [
                { value: '```\nObjectDetection.class_name: string\n```' },
                { value: 'Annotation class of the detection.' }
            ],
            range: expect.objectContaining({
                startLineNumber: 1,
                startColumn: 18,
                endLineNumber: 1,
                endColumn: 28
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

it.each([
    ['tp', 'True positive metric in the selected run.'],
    ['fp', 'False positive metric in the selected run.'],
    ['fn', 'False negative metric in the selected run.'],
    ['disagreement', 'Classification disagreement score in the selected run.'],
    ['miou', 'Mean intersection over union for semantic segmentation in the selected run.']
])('documents quoted evaluation metric %s inside nested criteria', async (name, description) => {
    const { getFieldHover } = await import('./getFieldHover');
    const text = `sample_evaluation(name = "run1" AND ("${name}" > 0))`;
    const startColumn = text.indexOf(`"${name}"`) + 2;
    const model = makeSyntaxDocModel({
        text,
        wordAtPosition: { word: name, startColumn, endColumn: startColumn + name.length },
        includeGetValue: true,
        includeGetOffsetAt: true
    });
    const hover = getFieldHover(model as never, { lineNumber: 1, column: startColumn } as never);
    expect(hover?.contents).toContainEqual({ value: description });
});
