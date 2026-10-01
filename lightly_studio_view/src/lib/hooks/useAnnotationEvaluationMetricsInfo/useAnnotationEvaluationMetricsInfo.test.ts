import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CreateQueryOptions, CreateQueryResult } from '@tanstack/svelte-query';
import * as tanstackQuery from '@tanstack/svelte-query';
import { getEvaluationAnnotationMetricsInfoOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { EvaluationRunAnnotationMetricsInfoView } from '$lib/api/lightly_studio_local/types.gen';
import { useAnnotationEvaluationMetricsInfo } from './useAnnotationEvaluationMetricsInfo.svelte';

describe('useAnnotationEvaluationMetricsInfo', () => {
    const queryResult = {
        data: [],
        isSuccess: true,
        subscribe: vi.fn()
    } as unknown as CreateQueryResult<EvaluationRunAnnotationMetricsInfoView[], Error>;

    beforeEach(() => {
        vi.resetAllMocks();
        vi.spyOn(tanstackQuery, 'createQuery').mockReturnValue(queryResult);
    });

    it('queries the metrics of the given annotation source', () => {
        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery');

        const result = useAnnotationEvaluationMetricsInfo({ collectionId: () => 'source-1' });

        const options = createQuerySpy.mock.calls[0][0]() as CreateQueryOptions;
        expect(options.queryKey).toEqual(
            getEvaluationAnnotationMetricsInfoOptions({ path: { collection_id: 'source-1' } })
                .queryKey
        );
        expect(result).toMatchObject({ data: [], isSuccess: true });
    });

    it('reads the collection ID through the getter, so switching sources refetches', () => {
        const createQuerySpy = vi.spyOn(tanstackQuery, 'createQuery');
        let collectionId = 'source-1';
        useAnnotationEvaluationMetricsInfo({ collectionId: () => collectionId });
        const optionsFn = createQuerySpy.mock.calls[0][0] as () => CreateQueryOptions;

        collectionId = 'source-2';

        expect(optionsFn().queryKey).toEqual(
            getEvaluationAnnotationMetricsInfoOptions({ path: { collection_id: 'source-2' } })
                .queryKey
        );
    });
});
