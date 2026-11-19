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
        expect(labels).not.toContain('event');
        expect(labels).not.toContain('frame');
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
        expect(labels).toContain('event');
        expect(labels).toContain('frame');
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

it.each([
    ['image', 'sample_evaluation', 'sample_evaluation(name = "run-name" AND "tp" >= 1)'],
    ['video', 'event', 'event(class_name = "..." AND start_time_s < 5)']
] as const)('inserts a valid %s query from the %s snippet', async (scope, label, expected) => {
    const { buildSchemaCompletions } = await import('./completionAdapterBuildSchemaCompletions');
    const range = { startLineNumber: 1, endLineNumber: 1, startColumn: 1, endColumn: 1 };
    const item = buildSchemaCompletions({ scope, range }).find((item) => item.label === label);
    const query = item?.insertText.replace(/\$\{\d+:([^}]+)\}/g, '$1');
    expect(query).toBe(expected);
    const parser = createLightlyQueryServices().LightlyQuery.parser.LangiumParser;
    expect(parseLightlyQuery(parser, query ?? '', scope).status).toBe('ok');
});

it('offers only event fields and boolean operators inside event()', async () => {
    const { buildSchemaCompletions } = await import('./completionAdapterBuildSchemaCompletions');
    const range = { startLineNumber: 1, endLineNumber: 1, startColumn: 1, endColumn: 1 };
    const items = buildSchemaCompletions({ scope: 'event', range });
    expect(items.map((item) => item.label)).toEqual([
        'class_name',
        'source',
        'confidence',
        'start_time_s',
        'end_time_s',
        'AND',
        'OR',
        'NOT'
    ]);
});

it('offers timestamp, annotations and boolean operators inside frame()', async () => {
    const { buildSchemaCompletions } = await import('./completionAdapterBuildSchemaCompletions');
    const range = { startLineNumber: 1, endLineNumber: 1, startColumn: 1, endColumn: 1 };
    const items = buildSchemaCompletions({ scope: 'frame', range });
    expect(items.map((item) => item.label)).toEqual([
        'frame_timestamp_s',
        'AND',
        'OR',
        'NOT',
        'object_detection',
        'classification',
        'segmentation_mask'
    ]);
});
