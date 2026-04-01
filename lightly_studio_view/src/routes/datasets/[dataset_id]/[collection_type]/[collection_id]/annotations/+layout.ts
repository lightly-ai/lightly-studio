import type { LayoutLoad, LayoutLoadEvent } from './$types';
import { useTags } from '$lib/hooks/useTags/useTags';

export const load: LayoutLoad = async ({ params: { collection_id } }: LayoutLoadEvent) => {
    const { tagsSelected } = useTags({
        collection_id: collection_id as string,
        kind: ['annotation']
    });

    return {
        annotationsSelectedTagsIds: tagsSelected
    };
};
