import { describe, expect, it, vi } from 'vitest';
import {
    CompletionItemKind as LspCompletionItemKind,
    InsertTextFormat as LspInsertTextFormat
} from 'vscode-languageserver-types';

vi.mock('monaco-editor', () => ({
    languages: {
        CompletionItemKind: {
            Field: 3,
            Function: 1,
            Text: 18,
            Snippet: 28,
            Keyword: 17
        },
        CompletionItemInsertTextRule: { InsertAsSnippet: 4 }
    }
}));

describe('lspToMonacoCompletion', () => {
    it('maps kind and uses fallback range/label when no textEdit', async () => {
        const { lspToMonacoCompletion } = await import('./completionAdapterLspToMonacoCompletion');
        const range = { startLineNumber: 2, endLineNumber: 2, startColumn: 1, endColumn: 4 };
        const result = lspToMonacoCompletion(
            { label: 'foo', kind: LspCompletionItemKind.Function },
            range as never,
            'image'
        );
        expect(result.kind).toBe(1);
        expect(result.range).toEqual(range);
        expect(result.insertText).toBe('foo');
    });

    it('uses textEdit range/newText and sets snippet rule', async () => {
        const { lspToMonacoCompletion } = await import('./completionAdapterLspToMonacoCompletion');
        const range = { startLineNumber: 1, endLineNumber: 1, startColumn: 1, endColumn: 1 };
        const result = lspToMonacoCompletion(
            {
                label: 'snippet',
                kind: LspCompletionItemKind.Snippet,
                insertTextFormat: LspInsertTextFormat.Snippet,
                textEdit: {
                    range: {
                        start: { line: 0, character: 4 },
                        end: { line: 0, character: 8 }
                    },
                    newText: 'foo($1)'
                }
            },
            range as never,
            'image'
        );
        expect(result.range).toEqual({
            startLineNumber: 1,
            endLineNumber: 1,
            startColumn: 5,
            endColumn: 9
        });
        expect(result.insertText).toBe('foo($1)');
        expect(result.insertTextRules).toBe(4);
    });
});
