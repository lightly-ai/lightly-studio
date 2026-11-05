import { describe, expect, it, vi } from 'vitest';
import { createLightlyQueryServices } from '../../language/lightly-query-module';
import { parseLightlyQuery } from '../../language/query-expr-translation';

vi.mock('monaco-editor', () => ({
    languages: {
        CompletionItemKind: { Field: 3, Keyword: 17 },
        CompletionItemInsertTextRule: { InsertAsSnippet: 4 }
    }
}));

describe('buildSchemaCompletions', () => {
    it('includes scope fields and top-level keywords in image scope except `video:`', async () => {
        const { buildSchemaCompletions } =
            await import('./completionAdapterBuildSchemaCompletions');
        const range = { startLineNumber: 1, endLineNumber: 1, startColumn: 1, endColumn: 1 };
        const items = buildSchemaCompletions({ scope: 'image', range });
        const labels = items.map((i) => i.label);
        expect(labels).toContain('width');
        expect(labels).not.toContain('video:');
        expect(labels).toContain('object_detection');
        expect(labels).toContain('segmentation_mask');
    });

    it('omits `video:` keyword in video scope', async () => {
        const { buildSchemaCompletions } =
            await import('./completionAdapterBuildSchemaCompletions');
        const range = { startLineNumber: 1, endLineNumber: 1, startColumn: 1, endColumn: 1 };
        const items = buildSchemaCompletions({ scope: 'video', range });
        const labels = items.map((i) => i.label);
        expect(labels).toContain('fps');
        expect(labels).not.toContain('video:');
    });

    it('includes segmentation mask fields in segmentation_mask scope', async () => {
        const { buildSchemaCompletions } =
            await import('./completionAdapterBuildSchemaCompletions');
        const range = { startLineNumber: 1, endLineNumber: 1, startColumn: 1, endColumn: 1 };
        const items = buildSchemaCompletions({ scope: 'segmentation_mask', range });
        const labels = items.map((i) => i.label);
        expect(labels).toContain('class_name');
        expect(labels).toContain('width');
        expect(labels).toContain('height');
    });
});

it('offers evaluation metrics and excludes unrelated sample fields and functions', async () => {
    const { buildSchemaCompletions } = await import('./completionAdapterBuildSchemaCompletions');
    const range = { startLineNumber: 1, endLineNumber: 1, startColumn: 1, endColumn: 1 };
    const items = buildSchemaCompletions({ scope: 'sample_evaluation', range });
    expect(items.map((item) => item.label)).toEqual([
        'name',
        '"tp"',
        '"fp"',
        '"fn"',
        '"disagreement"',
        '"miou"',
        'AND',
        'OR',
        'NOT'
    ]);
    const parser = createLightlyQueryServices().LightlyQuery.parser.LangiumParser;
    for (const name of ['tp', 'fp', 'fn', 'disagreement', 'miou']) {
        const item = items.find((item) => item.label === `"${name}"`);
        expect(item?.insertText).toBe(`"${name}"`);
        expect(item?.documentation).toBeTruthy();
        expect(
            parseLightlyQuery(
                parser,
                `sample_evaluation(name = "run1" AND ${item?.insertText} > 0)`
            ).status
        ).toBe('ok');
    }
});

it('inserts a valid evaluation query from the top-level snippet', async () => {
    const { buildSchemaCompletions } = await import('./completionAdapterBuildSchemaCompletions');
    const range = { startLineNumber: 1, endLineNumber: 1, startColumn: 1, endColumn: 1 };
    const item = buildSchemaCompletions({ scope: 'image', range }).find(
        (item) => item.label === 'sample_evaluation'
    );
    const query = item?.insertText.replace(/\$\{\d+:([^}]+)\}/g, '$1');
    expect(query).toBe('sample_evaluation(name = "run-name" AND "tp" >= 1)');
    const parser = createLightlyQueryServices().LightlyQuery.parser.LangiumParser;
    expect(parseLightlyQuery(parser, query ?? '').status).toBe('ok');
});
