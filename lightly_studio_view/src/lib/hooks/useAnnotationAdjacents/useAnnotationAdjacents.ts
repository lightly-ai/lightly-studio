import { readAnnotations } from '$lib/api/lightly_studio_local/sdk.gen';
import type {
    Annotation,
    SideEffectHook,
    SideEffectHookData,
    SideEffectHookResult
} from '$lib/services/types';
import { writable } from 'svelte/store';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

type UseAnnotationAdjacentsParams = {
    collection_id: string;
    cursor?: number;
    limit?: number;
    annotation_label_ids?: string[];
    tag_ids?: string[];
    annotationIndex: number;
    currentAnnotationId: string;
};

export type UseAnnotationAdjacentsData = {
    annotationNext?: Annotation;
    annotationPrevious?: Annotation;
};

export type UseAnnotationAdjacentsResult = SideEffectHookResult<UseAnnotationAdjacentsData>;

export const useAnnotationAdjacents: SideEffectHook<
    UseAnnotationAdjacentsData,
    UseAnnotationAdjacentsParams
> = ({ annotationIndex, ...loadingParams }): UseAnnotationAdjacentsResult => {
    const result = writable<SideEffectHookData<UseAnnotationAdjacentsData>>({
        isLoading: false
    });

    const _load = async () => {
        result.update((prev) => ({ ...prev, isLoading: true }));

        try {
            const { data: annotationsData } = await readAnnotations({
                path: { collection_id: loadingParams.collection_id },
                query: {
                    cursor: annotationIndex > 0 ? annotationIndex - 1 : 0,
                    limit: 3,
                    annotation_label_ids: loadingParams.annotation_label_ids,
                    tag_ids: loadingParams.tag_ids
                }
            });

            if (!annotationsData) {
                result.update((prev) => ({
                    ...prev,
                    isLoading: false,
                    error: 'No annotations data received',
                    data: undefined
                }));
                return;
            }

            const { setfilteredAnnotationCount } = useGlobalStorage();
            setfilteredAnnotationCount(annotationsData.total_count);

            let annotationNext = undefined;
            const annotationPrevious = annotationIndex > 0 ? annotationsData.data[0] : undefined;

            if (annotationsData.data.length > 1) {
                annotationNext =
                    annotationIndex === 0 ? annotationsData.data[1] : annotationsData.data[2];
            }

            result.update((prev) => ({
                ...prev,
                isLoading: false,
                error: undefined,
                data: {
                    annotationNext,
                    annotationPrevious
                }
            }));
        } catch (e) {
            result.update((prev) => ({ ...prev, isLoading: false, error: String(e) }));
        }
    };

    _load();

    return result;
};
