import type { LayoutLoad, LayoutLoadEvent } from './$types';
import { useTags } from '$lib/hooks/useTags/useTags';

export const load: LayoutLoad = async ({ parent, params: { dataset_id } }: LayoutLoadEvent) => {
    const { globalStorage } = await parent();

    const { tagsSelected } = useTags({
        dataset_id: dataset_id as string,
        kind: ['annotation']
    });

    return {
        annotationsSelectedTagsIds: tagsSelected,
        annotationsSelectedAnnotationLabelsIds: globalStorage.selectedAnnotationFilterIds
    };
};
