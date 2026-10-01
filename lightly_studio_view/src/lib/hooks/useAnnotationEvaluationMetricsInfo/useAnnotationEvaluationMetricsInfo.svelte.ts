import { getEvaluationAnnotationMetricsInfoOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { EvaluationRunAnnotationMetricsInfoView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';

interface UseAnnotationEvaluationMetricsInfoParams {
    /** Getter, so the query refetches when the browsed annotation source changes. */
    collectionId: () => string;
}

export const useAnnotationEvaluationMetricsInfo = ({
    collectionId
}: UseAnnotationEvaluationMetricsInfoParams): CreateQueryResult<
    EvaluationRunAnnotationMetricsInfoView[],
    Error
> => {
    return createQuery(() =>
        getEvaluationAnnotationMetricsInfoOptions({
            path: { collection_id: collectionId() }
        })
    );
};
