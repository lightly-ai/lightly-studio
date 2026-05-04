import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
    CompletionItemKind as LspCompletionItemKind,
    InsertTextFormat as LspInsertTextFormat,
    type CompletionItem as LspCompletionItem,
    type CompletionList as LspCompletionList
} from 'vscode-languageserver-types';
import type * as monaco from 'monaco-editor';

const mocks = vi.hoisted(() => ({
    registerCompletionItemProvider: vi.fn(),
    createLightlyQueryServices: vi.fn(),
    getCompletion: vi.fn(),
    deleteDocument: vi.fn(),
    createDocument: vi.fn(),
    build: vi.fn()
}));

vi.mock('monaco-editor', () => ({
    languages: {
        registerCompletionItemProvider: mocks.registerCompletionItemProvider,
        CompletionItemKind: {
            Method: 0,
            Function: 1,
            Constructor: 2,
            Field: 3,
            Variable: 4,
            Class: 5,
            Struct: 6,
            Interface: 7,
            Module: 8,
            Property: 9,
            Event: 10,
            Operator: 11,
            Unit: 12,
            Value: 13,
            Constant: 14,
            Enum: 15,
            EnumMember: 16,
            Keyword: 17,
            Text: 18,
            Color: 19,
            File: 20,
            Reference: 21,
            Folder: 23,
            TypeParameter: 24,
            Snippet: 28
        },
        CompletionItemInsertTextRule: {
            InsertAsSnippet: 4
        }
    }
}));

vi.mock('langium', async (importOriginal) => {
    const actual = await importOriginal<typeof import('langium')>();
    return {
        ...actual,
        URI: {
            ...actual.URI,
            parse: (value: string) => ({ toString: () => value })
        }
    };
});

vi.mock('../language/lightly-query-module', () => ({
    createLightlyQueryServices: mocks.createLightlyQueryServices
}));

interface ModelMock {
    uri: { toString: () => string };
    getValue: () => string;
    getWordUntilPosition: ReturnType<typeof vi.fn>;
    getOffsetAt: ReturnType<typeof vi.fn>;
}

function makeModel(
    value: string,
    word = { startColumn: 1, endColumn: value.length + 1 }
): ModelMock {
    return {
        uri: { toString: () => 'inmemory://model/1' },
        getValue: () => value,
        getWordUntilPosition: vi.fn(() => word),
        // Single-line tests: offset is just column - 1.
        getOffsetAt: vi.fn((pos: { lineNumber: number; column: number }) => pos.column - 1)
    };
}

async function loadAndAttach(items: LspCompletionItem[] | undefined): Promise<{
    provideCompletionItems: (
        model: monaco.editor.ITextModel,
        position: monaco.Position
    ) => Promise<monaco.languages.CompletionList>;
    triggerCharacters: string[] | undefined;
    languageId: string;
}> {
    const result: LspCompletionList | undefined =
        items === undefined ? undefined : { isIncomplete: false, items };
    mocks.getCompletion.mockResolvedValue(result);

    const { useSyntaxCompletion } = await import('./useSyntaxCompletion');
    useSyntaxCompletion({ languageId: 'lightly-query' });

    const [languageId, provider] = mocks.registerCompletionItemProvider.mock.calls[0];
    return {
        provideCompletionItems: provider.provideCompletionItems,
        triggerCharacters: provider.triggerCharacters,
        languageId
    };
}

describe('useSyntaxCompletion', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.resetModules();
        mocks.createLightlyQueryServices.mockReturnValue({
            shared: {
                workspace: {
                    LangiumDocuments: {
                        deleteDocument: mocks.deleteDocument,
                        createDocument: mocks.createDocument
                    },
                    DocumentBuilder: { build: mocks.build }
                }
            },
            LightlyQuery: {
                lsp: {
                    CompletionProvider: { getCompletion: mocks.getCompletion }
                }
            }
        });
        mocks.createDocument.mockImplementation((uri: { toString: () => string }) => ({
            uri,
            textDocument: { uri: uri.toString() }
        }));
        mocks.build.mockResolvedValue(undefined);
    });

    it('registers a Monaco completion provider with the supplied languageId and trigger characters', async () => {
        const { languageId, triggerCharacters } = await loadAndAttach([]);

        expect(mocks.registerCompletionItemProvider).toHaveBeenCalledOnce();
        expect(languageId).toBe('lightly-query');
        expect(triggerCharacters).toEqual(['.', ' ', '(', ':']);
    });

    it('returns no suggestions when the language service has no CompletionProvider', async () => {
        mocks.createLightlyQueryServices.mockReturnValueOnce({
            shared: {
                workspace: {
                    LangiumDocuments: {
                        deleteDocument: mocks.deleteDocument,
                        createDocument: mocks.createDocument
                    },
                    DocumentBuilder: { build: mocks.build }
                }
            },
            LightlyQuery: { lsp: { CompletionProvider: undefined } }
        });

        const { provideCompletionItems } = await loadAndAttach([]);
        const result = await provideCompletionItems(
            makeModel('q') as never,
            { lineNumber: 1, column: 2 } as never
        );

        expect(result).toEqual({ suggestions: [] });
        expect(mocks.getCompletion).not.toHaveBeenCalled();
    });

    it('rebuilds the Langium document and calls LSP getCompletion with 0-indexed position', async () => {
        const { provideCompletionItems } = await loadAndAttach([]);
        await provideCompletionItems(
            makeModel('width < 4') as never,
            { lineNumber: 3, column: 5 } as never
        );

        expect(mocks.deleteDocument).toHaveBeenCalledOnce();
        expect(mocks.createDocument).toHaveBeenCalledOnce();
        expect(mocks.build).toHaveBeenCalledOnce();

        const [, options] = mocks.build.mock.calls[0];
        expect(options).toEqual({ validation: false });

        expect(mocks.getCompletion).toHaveBeenCalledWith(expect.anything(), {
            textDocument: { uri: 'inmemory://model/1' },
            position: { line: 2, character: 4 }
        });
    });

    it('caches services so the LSP container is only created once', async () => {
        const first = await loadAndAttach([]);
        await first.provideCompletionItems(
            makeModel('q') as never,
            { lineNumber: 1, column: 2 } as never
        );
        await first.provideCompletionItems(
            makeModel('qq') as never,
            { lineNumber: 1, column: 3 } as never
        );

        expect(mocks.createLightlyQueryServices).toHaveBeenCalledOnce();
    });

    it('returns schema suggestions when LSP getCompletion resolves to undefined', async () => {
        const { provideCompletionItems } = await loadAndAttach(undefined);
        const result = await provideCompletionItems(
            makeModel('q') as never,
            { lineNumber: 1, column: 2 } as never
        );

        const labels = result.suggestions.map((suggestion) =>
            typeof suggestion.label === 'string' ? suggestion.label : suggestion.label.label
        );
        expect(labels).toContain('width');
        expect(labels).toContain('AND');
    });

    it('falls back to the word range under the cursor when the LSP item has no textEdit', async () => {
        const { provideCompletionItems } = await loadAndAttach([
            { label: 'foo', kind: LspCompletionItemKind.Keyword }
        ]);
        const result = await provideCompletionItems(
            makeModel('foo', { startColumn: 1, endColumn: 4 }) as never,
            { lineNumber: 2, column: 4 } as never
        );

        expect(result.suggestions[0].range).toEqual({
            startLineNumber: 2,
            endLineNumber: 2,
            startColumn: 1,
            endColumn: 4
        });
        expect(result.suggestions[0].insertText).toBe('foo');
    });

    it('uses the LSP textEdit range and newText when present (1-indexing them for Monaco)', async () => {
        const { provideCompletionItems } = await loadAndAttach([
            {
                label: 'replaceMe',
                kind: LspCompletionItemKind.Keyword,
                textEdit: {
                    range: {
                        start: { line: 0, character: 4 },
                        end: { line: 0, character: 9 }
                    },
                    newText: 'expanded'
                }
            }
        ]);
        const result = await provideCompletionItems(
            makeModel('something') as never,
            { lineNumber: 1, column: 5 } as never
        );

        expect(result.suggestions[0].range).toEqual({
            startLineNumber: 1,
            startColumn: 5,
            endLineNumber: 1,
            endColumn: 10
        });
        expect(result.suggestions[0].insertText).toBe('expanded');
    });

    it('marks snippet completions with InsertAsSnippet rules', async () => {
        const { provideCompletionItems } = await loadAndAttach([
            {
                label: 'plain',
                kind: LspCompletionItemKind.Keyword,
                insertTextFormat: LspInsertTextFormat.PlainText
            },
            {
                label: 'snippet',
                kind: LspCompletionItemKind.Snippet,
                insertTextFormat: LspInsertTextFormat.Snippet,
                insertText: 'foo($1)'
            }
        ]);
        const result = await provideCompletionItems(
            makeModel('') as never,
            { lineNumber: 1, column: 1 } as never
        );

        expect(result.suggestions[0].insertTextRules).toBeUndefined();
        expect(result.suggestions[1].insertTextRules).toBe(4);
        expect(result.suggestions[1].insertText).toBe('foo($1)');
    });

    it('maps the LSP completion kind to the equivalent Monaco kind', async () => {
        const { provideCompletionItems } = await loadAndAttach([
            { label: 'a', kind: LspCompletionItemKind.Field },
            { label: 'b', kind: LspCompletionItemKind.Function },
            { label: 'c' }
        ]);
        const result = await provideCompletionItems(
            makeModel('') as never,
            { lineNumber: 1, column: 1 } as never
        );

        expect(result.suggestions[0].kind).toBe(3);
        expect(result.suggestions[1].kind).toBe(1);
        expect(result.suggestions[2].kind).toBe(18);
    });

    it('preserves explicit LSP documentation (string and MarkupContent) without schema enrichment', async () => {
        const { provideCompletionItems } = await loadAndAttach([
            {
                label: 'Image',
                kind: LspCompletionItemKind.Class,
                documentation: 'plain doc'
            },
            {
                label: 'width',
                kind: LspCompletionItemKind.Field,
                documentation: { kind: 'markdown', value: '**bold**' }
            }
        ]);
        const result = await provideCompletionItems(
            makeModel('') as never,
            { lineNumber: 1, column: 1 } as never
        );

        expect(result.suggestions[0].documentation).toBe('plain doc');
        expect(result.suggestions[0].detail).toBeUndefined();
        expect(result.suggestions[1].documentation).toEqual({ value: '**bold**' });
    });

    it('enriches keyword labels with schema description when LSP omits documentation', async () => {
        const { provideCompletionItems } = await loadAndAttach([
            { label: 'AND', kind: LspCompletionItemKind.Keyword }
        ]);
        const result = await provideCompletionItems(
            makeModel('') as never,
            { lineNumber: 1, column: 1 } as never
        );

        expect(result.suggestions[0].detail).toBe('Boolean AND. Combines two conditions.');
        expect(result.suggestions[0].documentation).toEqual({
            value: 'Boolean AND. Combines two conditions.'
        });
    });

    it('enriches field labels with their owning scope and type metadata', async () => {
        const { provideCompletionItems } = await loadAndAttach([
            { label: 'fps', kind: LspCompletionItemKind.Field }
        ]);
        const result = await provideCompletionItems(
            makeModel('video: fps') as never,
            { lineNumber: 1, column: 11 } as never
        );

        expect(result.suggestions[0].detail).toBe('(field) Video.fps: float');
        expect(result.suggestions[0].documentation).toEqual({
            value: 'Frames per second. Equality only (`==`, `!=`).'
        });
    });

    it('suggests video-scope properties after `video:`', async () => {
        const { provideCompletionItems } = await loadAndAttach([]);
        const result = await provideCompletionItems(
            makeModel('video: ') as never,
            { lineNumber: 1, column: 8 } as never
        );

        const labels = result.suggestions.map((suggestion) =>
            typeof suggestion.label === 'string' ? suggestion.label : suggestion.label.label
        );

        expect(labels).toContain('fps');
        expect(labels).toContain('duration_s');
        expect(labels).toContain('file_name');
        expect(labels).not.toContain('created_at');
    });

    it('resolves field scope from cursor context (object_detection)', async () => {
        const { provideCompletionItems } = await loadAndAttach([
            { label: 'label', kind: LspCompletionItemKind.Field }
        ]);
        const result = await provideCompletionItems(
            makeModel('object_detection(label') as never,
            { lineNumber: 1, column: 23 } as never
        );

        expect(result.suggestions[0].detail).toBe('(field) ObjectDetection.label: string');
        expect(result.suggestions[0].documentation).toEqual({
            value: 'Class label of the detection.'
        });
    });

    it('leaves unknown labels untouched when neither LSP nor schema provides documentation', async () => {
        const { provideCompletionItems } = await loadAndAttach([
            { label: 'totally_unknown', kind: LspCompletionItemKind.Text }
        ]);
        const result = await provideCompletionItems(
            makeModel('') as never,
            { lineNumber: 1, column: 1 } as never
        );

        expect(result.suggestions[0].detail).toBeUndefined();
        expect(result.suggestions[0].documentation).toBeUndefined();
    });
});
