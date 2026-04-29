import { beforeEach, describe, expect, it, vi } from 'vitest';
import type * as monaco from 'monaco-editor';
import type { QueryExprTranslationResult } from './language/query-expr-translation';

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

vi.mock('./language/lightly-query-module', () => ({
    createLightlyQueryServices: mocks.createLightlyQueryServices
}));

vi.mock('./language/query-expr-translation', () => ({
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

type ParseResult = {
    lexerErrors?: unknown[];
    parserErrors?: unknown[];
};

async function loadHook(parseResult: ParseResult = {}) {
    mocks.parse.mockReturnValue({
        lexerErrors: [],
        parserErrors: [],
        value: {},
        ...parseResult
    });
    const { useLightlyQueryLanguage } = await import('./useLanguageService');
    return useLightlyQueryLanguage();
}

async function attachAndGetMarkers(
    parseResult: ParseResult,
    value = 'q'
): Promise<monaco.editor.IMarkerData[]> {
    const { attach } = await loadHook(parseResult);
    attach(makeModel(value) as never);
    return mocks.setModelMarkers.mock.calls[0][2] as monaco.editor.IMarkerData[];
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

    it('returns attach and translateQuery functions', async () => {
        const api = await loadHook();
        expect(typeof api.attach).toBe('function');
        expect(typeof api.translateQuery).toBe('function');
    });

    it('creates services lazily and caches them across hook calls', async () => {
        await loadHook();
        const { useLightlyQueryLanguage } = await import('./useLanguageService');
        useLightlyQueryLanguage();
        useLightlyQueryLanguage();
        expect(mocks.createLightlyQueryServices).toHaveBeenCalledOnce();
    });

    it('parses the model value and sets empty markers when there are no errors', async () => {
        const { attach } = await loadHook();
        const model = makeModel('width < 400');

        attach(model as never);

        expect(mocks.parse).toHaveBeenCalledWith('width < 400');
        expect(mocks.setModelMarkers).toHaveBeenCalledWith(model, 'lightly-query', []);
    });

    it('converts lexer errors into markers using line/column/length', async () => {
        const markers = await attachAndGetMarkers({
            lexerErrors: [{ message: 'unexpected character', line: 2, column: 5, length: 3 }]
        });

        expect(markers).toEqual([
            {
                severity: 8,
                message: 'unexpected character',
                startLineNumber: 2,
                startColumn: 5,
                endLineNumber: 2,
                endColumn: 8
            }
        ]);
    });

    it('falls back to defaults for missing lexer error coordinates', async () => {
        const markers = await attachAndGetMarkers({ lexerErrors: [{ message: 'oops' }] });

        expect(markers[0]).toMatchObject({
            startLineNumber: 1,
            startColumn: 1,
            endLineNumber: 1,
            endColumn: 2
        });
    });

    it('converts parser errors into markers and adds 1 to endColumn', async () => {
        const markers = await attachAndGetMarkers({
            parserErrors: [
                {
                    message: 'expected expression',
                    token: { startLine: 3, startColumn: 4, endLine: 3, endColumn: 9 }
                }
            ]
        });

        expect(markers).toEqual([
            {
                severity: 8,
                message: 'expected expression',
                startLineNumber: 3,
                startColumn: 4,
                endLineNumber: 3,
                endColumn: 10
            }
        ]);
    });

    it('falls back to defaults for parser errors without a token', async () => {
        const markers = await attachAndGetMarkers({ parserErrors: [{ message: 'mystery' }] });

        expect(markers[0]).toMatchObject({
            startLineNumber: 1,
            startColumn: 1,
            endLineNumber: 1,
            endColumn: 2
        });
    });

    it('combines lexer and parser errors into the marker list', async () => {
        const markers = await attachAndGetMarkers({
            lexerErrors: [{ message: 'lex', line: 1, column: 1, length: 1 }],
            parserErrors: [
                {
                    message: 'parse',
                    token: { startLine: 1, startColumn: 2, endLine: 1, endColumn: 3 }
                }
            ]
        });

        expect(markers.map((m) => m.message)).toEqual(['lex', 'parse']);
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
