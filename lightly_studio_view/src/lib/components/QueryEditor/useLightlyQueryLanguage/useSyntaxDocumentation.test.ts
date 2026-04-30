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
    getLineContent: ReturnType<typeof vi.fn>;
}

function makeModel(params: { wordAtPosition: WordAtPosition | null; line: string }): ModelMock {
    return {
        getWordAtPosition: vi.fn(() => params.wordAtPosition),
        getLineContent: vi.fn(() => params.line)
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

    it('returns receiver hover for receiver identifiers', async () => {
        const { useSyntaxDocumentation } = await import('./useSyntaxDocumentation');
        useSyntaxDocumentation({ languageId: 'lightly-query' });

        const provider = mocks.registerHoverProvider.mock.calls[0][1];
        const model = makeModel({
            wordAtPosition: { word: 'Image', startColumn: 1, endColumn: 6 },
            line: 'Image.width > 10'
        });
        const hover = provider.provideHover(model, { lineNumber: 1, column: 2 });

        expect(hover).toEqual({
            contents: [
                { value: '**Image** — Image sample. Filter expressions on a single image.' }
            ],
            range: expect.objectContaining({
                startLineNumber: 1,
                startColumn: 1,
                endLineNumber: 1,
                endColumn: 6
            })
        });
    });

    it('returns field hover for qualified receiver fields', async () => {
        const { useSyntaxDocumentation } = await import('./useSyntaxDocumentation');
        useSyntaxDocumentation({ languageId: 'lightly-query' });

        const provider = mocks.registerHoverProvider.mock.calls[0][1];
        const model = makeModel({
            wordAtPosition: { word: 'width', startColumn: 7, endColumn: 12 },
            line: 'Image.width > 10'
        });
        const hover = provider.provideHover(model, { lineNumber: 1, column: 8 });

        expect(hover).toEqual({
            contents: [
                { value: '```\nImage.width: int\n```' },
                { value: 'Image width in pixels.' }
            ],
            range: expect.objectContaining({
                startLineNumber: 1,
                startColumn: 7,
                endLineNumber: 1,
                endColumn: 12
            })
        });
    });

    it('returns null when no symbol documentation is available', async () => {
        const { useSyntaxDocumentation } = await import('./useSyntaxDocumentation');
        useSyntaxDocumentation({ languageId: 'lightly-query' });

        const provider = mocks.registerHoverProvider.mock.calls[0][1];
        const model = makeModel({
            wordAtPosition: { word: 'unknown', startColumn: 1, endColumn: 8 },
            line: 'unknown > 10'
        });
        const hover = provider.provideHover(model, { lineNumber: 1, column: 2 });

        expect(hover).toBeNull();
    });
});
