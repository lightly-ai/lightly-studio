import { describe, expect, it, vi } from 'vitest';

vi.mock('monaco-editor', () => ({
    languages: {
        CompletionItemKind: { Field: 3, Keyword: 17 },
        CompletionItemInsertTextRule: { InsertAsSnippet: 4 }
    }
}));

describe('buildSchemaCompletions', () => {
    it('includes scope fields and top-level keywords in image scope except `video:`', async () => {
        const { buildSchemaCompletions } = await import(
            './completionAdapterBuildSchemaCompletions'
        );
        const range = { startLineNumber: 1, endLineNumber: 1, startColumn: 1, endColumn: 1 };
        const items = buildSchemaCompletions('image', range as never);
        const labels = items.map((i) => i.label);
        expect(labels).toContain('width');
        expect(labels).not.toContain('video:');
        expect(labels).toContain('object_detection');
        expect(labels).toContain('segmentation_mask');
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

    it('includes segmentation mask fields in segmentation_mask scope', async () => {
        const { buildSchemaCompletions } = await import(
            './completionAdapterBuildSchemaCompletions'
        );
        const range = { startLineNumber: 1, endLineNumber: 1, startColumn: 1, endColumn: 1 };
        const items = buildSchemaCompletions('segmentation_mask', range as never);
        const labels = items.map((i) => i.label);
        expect(labels).toContain('label');
        expect(labels).toContain('width');
        expect(labels).toContain('height');
    });
});
