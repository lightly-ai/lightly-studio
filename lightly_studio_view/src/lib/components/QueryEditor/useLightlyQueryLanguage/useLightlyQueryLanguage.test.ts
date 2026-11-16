import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { QueryExprTranslationResult } from '../language/query-expr-translation';

const mocks = vi.hoisted(() => ({
    setModelMarkers: vi.fn(),
    registerHoverProvider: vi.fn(),
    createLightlyQueryServices: vi.fn(),
    parse: vi.fn(),
    parseLightlyQuery: vi.fn()
}));

vi.mock('monaco-editor', () => ({
    editor: { setModelMarkers: mocks.setModelMarkers },
    languages: { registerHoverProvider: mocks.registerHoverProvider },
    Range: class {},
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

    it('flags incompatible scope before Apply and clears the error after correction', async () => {
        const { attach } = await loadHook();
        const { createLightlyQueryServices } = await vi.importActual<
            typeof import('../language/lightly-query-module')
        >('../language/lightly-query-module');
        const parser = createLightlyQueryServices().LightlyQuery.parser.LangiumParser;
        mocks.parse.mockImplementation((text: string) => parser.parse(text));
        const model = makeModel('# comment\nvideo: duration_s > 10');
        attach(model as never, 'image');
        expect(mocks.setModelMarkers.mock.calls.at(-1)![2]).toEqual([
            expect.objectContaining({
                message: 'Video queries cannot be applied to an image collection.',
                severity: 8,
                startLineNumber: 2,
                startColumn: 1
            })
        ]);

        model._value = 'width > 100';
        model.onDidChangeContent.mock.calls[0][0]();
        expect(mocks.setModelMarkers.mock.calls.at(-1)![2]).toEqual([]);
        for (const value of ['duration_s > 10', 'video: duration_s > 10']) {
            attach(makeModel(value) as never, 'video');
            expect(mocks.setModelMarkers.mock.calls.at(-1)![2]).toEqual([]);
        }
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

        expect(mocks.parseLightlyQuery).toHaveBeenCalledWith(
            { parse: mocks.parse },
            'width < 400',
            undefined
        );
        expect(result).toBe(expected);
    });
});

it('maps video diagnostics to visible lines and keeps model scopes independent', async () => {
    const { attach } = await loadHook({
        lexerErrors: [{ message: 'unexpected character', line: 3, column: 14 }],
        parserErrors: [
            {
                message: 'invalid token',
                token: { startLine: 3, startColumn: 14, endLine: 3, endColumn: 14 }
            }
        ]
    });
    const video = makeModel('# comment\nduration_s > @');
    attach(video as never, 'video');
    const markers = mocks.setModelMarkers.mock.calls.at(-1)![2];
    expect(markers).toHaveLength(2);
    for (const marker of markers) {
        expect(marker).toMatchObject({ startLineNumber: 2, endLineNumber: 2, startColumn: 14 });
    }
    const { getModelQuerySource } = await import('./modelQueryScope');
    expect(getModelQuerySource(makeModel('width > 1') as never).text).toBe('width > 1');
});
