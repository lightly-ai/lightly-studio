import type { LayoutLoad, LayoutLoadEvent } from './$types';
import { useTags } from '$lib/hooks/useTags/useTags';

export const load: LayoutLoad = async ({ parent, params: { collection_id } }: LayoutLoadEvent) => {
    const { globalStorage } = await parent();

    // Use autoLoad: false - tags will be loaded in AnnotationsGrid onMount, not during preload
    const { tagsSelected } = useTags({
        collection_id: collection_id as string,
        kind: ['annotation'],
        autoLoad: false
    });

    return {
        annotationsSelectedTagsIds: tagsSelected,
        annotationsSelectedAnnotationLabelsIds: globalStorage.selectedAnnotationFilterIds
    };
};
