import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { QueryExprTranslationResult } from '../language/query-expr-translation';

const mocks = vi.hoisted(() => ({
    setModelMarkers: vi.fn(),
    createLightlyQueryServices: vi.fn(),
    parse: vi.fn(),
    parseLightlyQuery: vi.fn()
}));

vi.mock('monaco-editor', () => ({
    editor: { setModelMarkers: mocks.setModelMarkers },
    MarkerSeverity: { Error: 8 }
}));

vi.mock('../language/lightly-query-module', () => ({
    createLightlyQueryServices: mocks.createLightlyQueryServices
}));

vi.mock('../language/query-expr-translation', () => ({
    parseLightlyQuery: mocks.parseLightlyQuery
}));

interface ModelMock {
    getValue: () => string;
    onDidChangeContent: ReturnType<typeof vi.fn>;
    _value: string;
}

function makeModel(value: string, contentDispose = vi.fn()): ModelMock {
    return {
        _value: value,
        getValue() {
            return this._value;
        },
        onDidChangeContent: vi.fn(() => ({ dispose: contentDispose }))
    };
}

type ParseResult = { lexerErrors?: unknown[]; parserErrors?: unknown[] };

async function loadHook(parseResult: ParseResult = {}) {
    mocks.parse.mockReturnValue({
        lexerErrors: [],
        parserErrors: [],
        value: {},
        ...parseResult
    });
    const { useLightlyQueryLanguage } = await import('./useLightlyQueryLanguage');
    return useLightlyQueryLanguage();
}

describe('useLightlyQueryLanguage', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.resetModules();
        mocks.createLightlyQueryServices.mockReturnValue({
            shared: {},
            LightlyQuery: { parser: { LangiumParser: { parse: mocks.parse } } }
        });
    });

    it('creates services lazily and caches them across hook calls', async () => {
        await loadHook();
        const { useLightlyQueryLanguage } = await import('./useLightlyQueryLanguage');
        useLightlyQueryLanguage();
        useLightlyQueryLanguage();
        expect(mocks.createLightlyQueryServices).toHaveBeenCalledOnce();
    });

    it('parses the model value and clears markers when there are no errors', async () => {
        const { attach } = await loadHook();
        const model = makeModel('width < 400');

        attach(model as never);

        expect(mocks.parse).toHaveBeenCalledWith('width < 400');
        expect(mocks.setModelMarkers).toHaveBeenCalledWith(model, 'lightly-query', []);
    });

    it('forwards lexer errors before parser errors to setModelMarkers', async () => {
        const { attach } = await loadHook({
            lexerErrors: [{ message: 'lex' }],
            parserErrors: [{ message: 'parse' }]
        });
        attach(makeModel('q') as never);

        const markers = mocks.setModelMarkers.mock.calls[0][2];
        expect(markers.map((m: { message: string }) => m.message)).toEqual(['lex', 'parse']);
    });

    it('re-validates the model whenever its content changes', async () => {
        const { attach } = await loadHook();
        const model = makeModel('first');
        attach(model as never);

        const listener = model.onDidChangeContent.mock.calls[0][0] as () => void;
        model._value = 'second';
        listener();

        expect(mocks.parse).toHaveBeenCalledTimes(2);
        expect(mocks.parse).toHaveBeenLastCalledWith('second');
    });

    it('disposes the content subscription and clears markers on cleanup', async () => {
        const contentDispose = vi.fn();
        const { attach } = await loadHook();
        const model = makeModel('q', contentDispose);
        const detach = attach(model as never);

        mocks.setModelMarkers.mockClear();
        detach();

        expect(contentDispose).toHaveBeenCalledOnce();
        expect(mocks.setModelMarkers).toHaveBeenCalledWith(model, 'lightly-query', []);
    });

    it('delegates translateQuery to parseLightlyQuery with the cached parser', async () => {
        const expected: QueryExprTranslationResult = {
            status: 'ok',
            queryExpr: {
                match_expr: {
                    type: 'integer_expr',
                    field: { table: 'image', name: 'width' },
                    operator: '<',
                    value: 400
                }
            }
        };
        mocks.parseLightlyQuery.mockReturnValue(expected);

        const { translateQuery } = await loadHook();
        const result = translateQuery('width < 400');

        expect(mocks.parseLightlyQuery).toHaveBeenCalledWith({ parse: mocks.parse }, 'width < 400');
        expect(result).toBe(expected);
    });
});
