import { describe, expect, it } from 'vitest';
import { isEqual } from 'lodash-es';
import { mergeExternalFilters, paramsWithoutExternalFilters } from './syncFilterParams';
import type { ImagesInfiniteParams } from '$lib/hooks/useImagesInfinite/useImagesInfinite';
import type { NormalModeFilters } from '$lib/hooks/useImagesInfinite/types';

const confusionCell = {
    evaluation_run_id: 'run-1',
    gt_label: 'cat',
    pred_label: 'dog'
};

const embeddingRegion = {
    polygon: [
        { x: 0, y: 0 },
        { x: 1, y: 0 },
        { x: 1, y: 1 }
    ]
};

const normalParams = (collection_id: string, filters: NormalModeFilters): ImagesInfiniteParams => ({
    collection_id,
    mode: 'normal',
    filters
});

const baseNormalParams = (collection_id = 'col-1'): ImagesInfiniteParams =>
    normalParams(collection_id, { tag_ids: ['tag-1'] });

describe('paramsWithoutExternalFilters', () => {
    it('strips sample_ids and confusion_cell from normal-mode filters', () => {
        const params = normalParams('col-1', {
            tag_ids: ['tag-1'],
            sample_ids: ['s1', 's2'],
            confusion_cell: confusionCell
        });

        expect(paramsWithoutExternalFilters(params).filters).toEqual({ tag_ids: ['tag-1'] });
    });

    it('treats params that differ only in sample_ids/embedding_region/confusion_cell as equal', () => {
        const base = baseNormalParams();
        const withExternal = normalParams('col-1', {
            tag_ids: ['tag-1'],
            sample_ids: ['s1'],
            embedding_region: embeddingRegion,
            confusion_cell: confusionCell
        });

        expect(
            isEqual(paramsWithoutExternalFilters(base), paramsWithoutExternalFilters(withExternal))
        ).toBe(true);
    });

    it('keeps params that differ in other filters distinct', () => {
        const base = baseNormalParams();
        const other = normalParams('col-1', { tag_ids: ['tag-2'] });

        expect(
            isEqual(paramsWithoutExternalFilters(base), paramsWithoutExternalFilters(other))
        ).toBe(false);
    });

    it('drops filters entirely for classifier mode', () => {
        const params: ImagesInfiniteParams = {
            collection_id: 'col-1',
            mode: 'classifier',
            classifierSamples: { positiveSampleIds: ['s1'], negativeSampleIds: [] }
        };

        expect(paramsWithoutExternalFilters(params).filters).toBeUndefined();
    });
});

describe('mergeExternalFilters', () => {
    it('carries sample_ids from the previous params into the base params', () => {
        const baseParams = baseNormalParams();
        const currentParams = normalParams('col-1', {
            tag_ids: ['tag-1'],
            sample_ids: ['s1', 's2']
        });

        const result = mergeExternalFilters(baseParams, currentParams);

        expect(result.mode).toBe('normal');
        if (result.mode === 'normal') {
            expect(result.filters?.sample_ids).toEqual(['s1', 's2']);
            expect(result.filters?.tag_ids).toEqual(['tag-1']);
        }
    });

    it('carries the embedding_region forward across collections', () => {
        const baseParams = baseNormalParams('col-2');
        const currentParams = normalParams('col-1', { embedding_region: embeddingRegion });

        const result = mergeExternalFilters(baseParams, currentParams);

        if (result.mode === 'normal') {
            expect(result.filters?.embedding_region).toEqual(embeddingRegion);
        }
    });

    it('carries the confusion_cell forward when the collection matches', () => {
        const baseParams = baseNormalParams('col-1');
        const currentParams = normalParams('col-1', { confusion_cell: confusionCell });

        const result = mergeExternalFilters(baseParams, currentParams);

        if (result.mode === 'normal') {
            expect(result.filters?.confusion_cell).toEqual(confusionCell);
        }
    });

    it('drops the confusion_cell when navigating to a different collection', () => {
        const baseParams = baseNormalParams('col-2');
        const currentParams = normalParams('col-1', { confusion_cell: confusionCell });

        const result = mergeExternalFilters(baseParams, currentParams);

        if (result.mode === 'normal') {
            expect(result.filters?.confusion_cell).toBeUndefined();
        }
    });

    it('keeps sample_ids but drops a stale confusion_cell across collections', () => {
        const baseParams = baseNormalParams('col-2');
        const currentParams = normalParams('col-1', {
            sample_ids: ['s1'],
            confusion_cell: confusionCell
        });

        const result = mergeExternalFilters(baseParams, currentParams);

        if (result.mode === 'normal') {
            expect(result.filters?.sample_ids).toEqual(['s1']);
            expect(result.filters?.confusion_cell).toBeUndefined();
        }
    });

    it('returns the base params unchanged when there are no external filters', () => {
        const baseParams = baseNormalParams();
        const currentParams = baseNormalParams();

        const result = mergeExternalFilters(baseParams, currentParams);

        expect(result).toBe(baseParams);
    });

    it('returns the base params unchanged when the previous params are not normal mode', () => {
        const baseParams = baseNormalParams();
        const currentParams: ImagesInfiniteParams = {
            collection_id: 'col-1',
            mode: 'classifier',
            classifierSamples: { positiveSampleIds: ['s1'], negativeSampleIds: [] }
        };

        const result = mergeExternalFilters(baseParams, currentParams);

        expect(result).toBe(baseParams);
    });
});
