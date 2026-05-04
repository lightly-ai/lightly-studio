import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
    registerHoverProvider: vi.fn(),
    getHover: vi.fn()
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

vi.mock('./syntaxDocumentation/getHover', () => ({
    getHover: mocks.getHover
}));

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

    it('delegates provideHover to getHover orchestration', async () => {
        const { useSyntaxDocumentation } = await import('./useSyntaxDocumentation');
        useSyntaxDocumentation({ languageId: 'lightly-query' });

        const provider = mocks.registerHoverProvider.mock.calls[0][1];
        const model = {} as never;
        const position = { lineNumber: 1, column: 1 } as never;
        const expected = { contents: [{ value: 'x' }], range: null } as never;
        mocks.getHover.mockReturnValueOnce(expected);
        const hover = provider.provideHover(model, position);

        expect(mocks.getHover).toHaveBeenCalledWith(model, position);
        expect(hover).toBe(expected);
    });
});
