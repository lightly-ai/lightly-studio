import { get, writable } from 'svelte/store';
import { flushSync } from 'svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { MetadataInfoView } from '$lib/api/lightly_studio_local';
import type { EvaluationRunMetricsInfoView } from '$lib/api/lightly_studio_local/types.gen';
import { useSortFields } from './useSortFields.svelte';

const metadataInfo = writable<MetadataInfoView[]>([]);

// In TanStack v6, useEvaluationSampleMetricsInfo returns a reactive proxy (not a store).
// Mock it as a plain object with .data and .dataUpdatedAt properties.
const metricsInfoMock: { data: EvaluationRunMetricsInfoView[] | null; dataUpdatedAt: number } = {
    data: null,
    dataUpdatedAt: 0
};

vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', () => ({
    useMetadataFilters: () => ({ metadataInfo })
}));

vi.mock('$lib/hooks/useEvaluationSampleMetricsInfo/useEvaluationSampleMetricsInfo', () => ({
    useEvaluationSampleMetricsInfo: () => metricsInfoMock
}));

describe('useSortFields', () => {
    beforeEach(() => {
        metadataInfo.set([]);
        metricsInfoMock.data = null;
        metricsInfoMock.dataUpdatedAt = 0;
    });

    describe('allSortFields', () => {
        it('contains the five base image sort fields', () => {
            const { allSortFields } = useSortFields({ datasetId: 'ds1' });
            flushSync();
            const fields = get(allSortFields);

            expect(fields).toEqual(
                expect.arrayContaining([
                    expect.objectContaining({ source: 'image', value: 'file_name' }),
                    expect.objectContaining({ source: 'image', value: 'file_path_abs' }),
                    expect.objectContaining({ source: 'image', value: 'created_at' }),
                    expect.objectContaining({ source: 'image', value: 'width' }),
                    expect.objectContaining({ source: 'image', value: 'height' })
                ])
            );
        });

        it('includes metadata fields of supported types with metadata. prefix label', () => {
            metadataInfo.set([
                { name: 'score', type: 'float' },
                { name: 'count', type: 'integer' },
                { name: 'label', type: 'string' },
                { name: 'active', type: 'boolean' }
            ]);
            const { allSortFields } = useSortFields({ datasetId: 'ds1' });
            flushSync();
            const fields = get(allSortFields);

            expect(fields).toEqual(
                expect.arrayContaining([
                    expect.objectContaining({
                        source: 'metadata',
                        value: 'score',
                        label: 'metadata.score',
                        is_numeric: true
                    }),
                    expect.objectContaining({
                        source: 'metadata',
                        value: 'count',
                        label: 'metadata.count',
                        is_numeric: true
                    }),
                    expect.objectContaining({
                        source: 'metadata',
                        value: 'label',
                        label: 'metadata.label',
                        is_numeric: false
                    }),
                    expect.objectContaining({
                        source: 'metadata',
                        value: 'active',
                        label: 'metadata.active',
                        is_numeric: false
                    })
                ])
            );
        });

        it('excludes list and dict metadata fields', () => {
            metadataInfo.set([
                { name: 'tags', type: 'list' },
                { name: 'nested', type: 'dict' },
                { name: 'score', type: 'float' }
            ]);
            const { allSortFields } = useSortFields({ datasetId: 'ds1' });
            flushSync();
            const fields = get(allSortFields);

            expect(fields.map((f) => ('value' in f ? f.value : null))).not.toContain('tags');
            expect(fields.map((f) => ('value' in f ? f.value : null))).not.toContain('nested');
        });

        it('includes evaluation metric fields with run_name_metric_name label', () => {
            metricsInfoMock.data = [
                {
                    run_name: 'run1',
                    metrics: [
                        { metric_name: 'precision', min_value: 0, max_value: 1 },
                        { metric_name: 'recall', min_value: 0, max_value: 1 }
                    ]
                }
            ];
            const { allSortFields } = useSortFields({ datasetId: 'ds1' });
            flushSync();
            const fields = get(allSortFields);

            expect(fields).toEqual(
                expect.arrayContaining([
                    expect.objectContaining({
                        source: 'evaluation_metric',
                        evaluation_run_name: 'run1',
                        metric_name: 'precision',
                        label: 'run1_precision'
                    }),
                    expect.objectContaining({
                        source: 'evaluation_metric',
                        evaluation_run_name: 'run1',
                        metric_name: 'recall',
                        label: 'run1_recall'
                    })
                ])
            );
        });

        it('updates reactively when metadataInfo changes', () => {
            const { allSortFields } = useSortFields({ datasetId: 'ds1' });
            flushSync();

            expect(
                get(allSortFields).find((f) => 'value' in f && f.value === 'brightness')
            ).toBeUndefined();

            metadataInfo.set([{ name: 'brightness', type: 'float' }]);

            expect(
                get(allSortFields).find((f) => 'value' in f && f.value === 'brightness')
            ).toBeDefined();
        });
    });
});
