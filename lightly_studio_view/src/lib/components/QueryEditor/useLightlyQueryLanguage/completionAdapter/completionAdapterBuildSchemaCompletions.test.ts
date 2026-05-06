import { describe, expect, it, vi } from 'vitest';

vi.mock('monaco-editor', () => ({
    languages: {
        CompletionItemKind: { Field: 3, Keyword: 17 },
        CompletionItemInsertTextRule: { InsertAsSnippet: 4 }
    }
}));

describe('buildSchemaCompletions', () => {
    it('includes scope fields and top-level keywords in image scope', async () => {
        const { buildSchemaCompletions } = await import(
            './completionAdapterBuildSchemaCompletions'
        );
        const range = { startLineNumber: 1, endLineNumber: 1, startColumn: 1, endColumn: 1 };
        const items = buildSchemaCompletions('image', range as never);
        const labels = items.map((i) => i.label);
        expect(labels).toContain('width');
        expect(labels).toContain('video:');
        expect(labels).toContain('object_detection');
    });

    it('omits `video:` keyword in video scope', async () => {
        const { buildSchemaCompletions } = await import(
            './completionAdapterBuildSchemaCompletions'
        );
        const range = { startLineNumber: 1, endLineNumber: 1, startColumn: 1, endColumn: 1 };
        const items = buildSchemaCompletions('video', range as never);
        const labels = items.map((i) => i.label);
        expect(labels).toContain('fps');
        expect(labels).not.toContain('video:');
    });
});
