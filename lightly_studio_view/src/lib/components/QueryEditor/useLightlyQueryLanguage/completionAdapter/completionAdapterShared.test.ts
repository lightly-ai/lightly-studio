import { describe, expect, it, vi } from 'vitest';
import { CompletionItemKind as LspCompletionItemKind } from 'vscode-languageserver-types';

vi.mock('monaco-editor', () => ({
    languages: {
        CompletionItemKind: {
            Text: 18,
            Method: 0,
            Function: 1,
            Constructor: 2,
            Field: 3,
            Variable: 4,
            Class: 5,
            Interface: 7,
            Module: 8,
            Property: 9,
            Unit: 12,
            Value: 13,
            Enum: 15,
            Keyword: 17,
            Snippet: 28,
            Color: 19,
            File: 20,
            Reference: 21,
            Folder: 23,
            EnumMember: 16,
            Constant: 14,
            Struct: 6,
            Event: 10,
            Operator: 11,
            TypeParameter: 24
        }
    }
}));

describe('completionAdapterShared', () => {
    it('defines allowed nested keywords', async () => {
        const { ALLOWED_NESTED_KEYWORDS } = await import('./completionAdapterShared');
        expect(ALLOWED_NESTED_KEYWORDS.has('AND')).toBe(true);
        expect(ALLOWED_NESTED_KEYWORDS.has('OR')).toBe(true);
        expect(ALLOWED_NESTED_KEYWORDS.has('NOT')).toBe(true);
        expect(ALLOWED_NESTED_KEYWORDS.has('IN')).toBe(false);
    });

    it('maps LSP kinds to Monaco kinds', async () => {
        const { LSP_TO_MONACO_KIND } = await import('./completionAdapterShared');
        expect(LSP_TO_MONACO_KIND[LspCompletionItemKind.Text]).toBe(18);
        expect(LSP_TO_MONACO_KIND[LspCompletionItemKind.Function]).toBe(1);
        expect(LSP_TO_MONACO_KIND[LspCompletionItemKind.Keyword]).toBe(17);
    });
});
