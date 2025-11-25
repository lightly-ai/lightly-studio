import type { LayoutLoad, LayoutLoadEvent } from './$types';
import { useTags } from '$lib/hooks/useTags/useTags';
import { useRootDataset } from '$lib/hooks/useRootDataset/useRootDataset';

export const load: LayoutLoad = async ({ parent }: LayoutLoadEvent) => {
    const { globalStorage } = await parent();

    // Get root dataset ID - tags and annotation labels should use root dataset, not the annotation dataset
    const rootDataset = await useRootDataset();
    const rootDatasetId = rootDataset.dataset_id;

    const { tagsSelected } = useTags({
        dataset_id: rootDatasetId,
        kind: ['annotation']
    });

    return {
        annotationsSelectedTagsIds: tagsSelected,
        annotationsSelectedAnnotationLabelsIds: globalStorage.selectedAnnotationFilterIds,
        rootDatasetId
    };
};
