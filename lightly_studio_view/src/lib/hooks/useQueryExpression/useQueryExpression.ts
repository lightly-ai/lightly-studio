import type { Writable } from 'svelte/store';
import type { RootScope } from '$lib/components/QueryEditor/language/types';
import { useImageFilters, type QueryExpression } from '$lib/hooks/useImageFilters/useImageFilters';
import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';

interface UseQueryExpressionReturn {
    queryExpression: Writable<QueryExpression | null>;
    updateQueryExpr: (expr?: QueryExpression) => void;
}

/** Returns the query filter state of the images grid or of the videos grid. */
export function useQueryExpression(rootScope: RootScope): UseQueryExpressionReturn {
    if (rootScope === 'video') {
        const { videoQueryExpression, updateQueryExpr } = useVideoFilters();
        return { queryExpression: videoQueryExpression, updateQueryExpr };
    }
    const { imageQueryExpression, updateQueryExpr } = useImageFilters();
    return { queryExpression: imageQueryExpression, updateQueryExpr };
}
