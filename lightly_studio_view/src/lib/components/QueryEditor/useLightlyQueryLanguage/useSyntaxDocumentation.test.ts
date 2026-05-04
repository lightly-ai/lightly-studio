import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
    registerHoverProvider: vi.fn()
}));

vi.mock('monaco-editor', () => ({
    languages: {
        registerHoverProvider: mocks.registerHoverProvider
    },
    Range: class Range {
        constructor(
            public startLineNumber: number,
            public startColumn: number,
            public endLineNumber: number,
            public endColumn: number
        ) {}
    }
}));

interface WordAtPosition {
    word: string;
    startColumn: number;
    endColumn: number;
}

interface ModelMock {
    getWordAtPosition: ReturnType<typeof vi.fn>;
    getValue: ReturnType<typeof vi.fn>;
    getOffsetAt: ReturnType<typeof vi.fn>;
}

function makeModel(params: { text: string; wordAtPosition: WordAtPosition | null }): ModelMock {
    return {
        getWordAtPosition: vi.fn(() => params.wordAtPosition),
        getValue: vi.fn(() => params.text),
        // Single-line tests: offset is just column - 1.
        getOffsetAt: vi.fn((pos: { lineNumber: number; column: number }) => pos.column - 1)
    };
}

describe('useSyntaxDocumentation', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.resetModules();
    });

    it('registers a hover provider for the given language id', async () => {
        const { useSyntaxDocumentation } = await import('./useSyntaxDocumentation');
        useSyntaxDocumentation({ languageId: 'lightly-query' });

        expect(mocks.registerHoverProvider).toHaveBeenCalledOnce();
        expect(mocks.registerHoverProvider).toHaveBeenCalledWith(
            'lightly-query',
            expect.objectContaining({ provideHover: expect.any(Function) })
        );
    });

    it('skips re-registering when called again with the same language id', async () => {
        const { useSyntaxDocumentation } = await import('./useSyntaxDocumentation');
        useSyntaxDocumentation({ languageId: 'lightly-query' });
        useSyntaxDocumentation({ languageId: 'lightly-query' });

        expect(mocks.registerHoverProvider).toHaveBeenCalledOnce();
    });

    it('returns keyword hover for top-level keywords', async () => {
        const { useSyntaxDocumentation } = await import('./useSyntaxDocumentation');
        useSyntaxDocumentation({ languageId: 'lightly-query' });

        const provider = mocks.registerHoverProvider.mock.calls[0][1];
        const model = makeModel({
            text: 'width > 10 AND height < 20',
            wordAtPosition: { word: 'AND', startColumn: 12, endColumn: 15 }
        });
        const hover = provider.provideHover(model, { lineNumber: 1, column: 13 });

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

    it('returns image-scope field hover at top level', async () => {
        const { useSyntaxDocumentation } = await import('./useSyntaxDocumentation');
        useSyntaxDocumentation({ languageId: 'lightly-query' });

        const provider = mocks.registerHoverProvider.mock.calls[0][1];
        const model = makeModel({
            text: 'width > 10',
            wordAtPosition: { word: 'width', startColumn: 1, endColumn: 6 }
        });
        const hover = provider.provideHover(model, { lineNumber: 1, column: 2 });

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

    it('returns video-scope field hover after the `video:` prefix', async () => {
        const { useSyntaxDocumentation } = await import('./useSyntaxDocumentation');
        useSyntaxDocumentation({ languageId: 'lightly-query' });

        const provider = mocks.registerHoverProvider.mock.calls[0][1];
        const model = makeModel({
            text: 'video: fps == 30',
            wordAtPosition: { word: 'fps', startColumn: 8, endColumn: 11 }
        });
        const hover = provider.provideHover(model, { lineNumber: 1, column: 9 });

        expect(hover).toEqual({
            contents: [
                { value: '```\nVideo.fps: float\n```' },
                { value: 'Frames per second. Equality only (`==`, `!=`).' }
            ],
            range: expect.objectContaining({
                startLineNumber: 1,
                startColumn: 8,
                endLineNumber: 1,
                endColumn: 11
            })
        });
    });

    it('returns object-detection field hover inside object_detection(...)', async () => {
        const { useSyntaxDocumentation } = await import('./useSyntaxDocumentation');
        useSyntaxDocumentation({ languageId: 'lightly-query' });

        const provider = mocks.registerHoverProvider.mock.calls[0][1];
        const model = makeModel({
            text: 'object_detection(label == "cat")',
            wordAtPosition: { word: 'label', startColumn: 18, endColumn: 23 }
        });
        const hover = provider.provideHover(model, { lineNumber: 1, column: 19 });

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

    it('returns null when no symbol documentation is available', async () => {
        const { useSyntaxDocumentation } = await import('./useSyntaxDocumentation');
        useSyntaxDocumentation({ languageId: 'lightly-query' });

        const provider = mocks.registerHoverProvider.mock.calls[0][1];
        const model = makeModel({
            text: 'unknown > 10',
            wordAtPosition: { word: 'unknown', startColumn: 1, endColumn: 8 }
        });
        const hover = provider.provideHover(model, { lineNumber: 1, column: 2 });

        expect(hover).toBeNull();
    });
});
