import { derived, readonly, writable, type Readable } from 'svelte/store';
import type { GetEmbeddings2dRequest } from '$lib/api/lightly_studio_local/types.gen';
import type { PlotColorByType } from '../PlotColorByPopover/usePlotColorByType/usePlotColorByType';

type ColorBy = GetEmbeddings2dRequest['color_by'];

interface UsePlotColorByParams {
    selectedColorByType: Readable<PlotColorByType | null>;
    tags: Readable<{ tag_id: string }[]>;
    annotationLabels: Readable<{ annotation_label_id: string }[]>;
}

interface UsePlotColorByReturn {
    colorBy: Readable<ColorBy>;
    selectedColorByKey: Readable<string | null>;
    setSelectedColorByKey: (key: string | null) => void;
}

export function usePlotColorBy({
    selectedColorByType,
    tags,
    annotationLabels
}: UsePlotColorByParams): UsePlotColorByReturn {
    const selectedColorByKey = writable<string | null>(null);

    const colorBy = derived(
        [selectedColorByType, selectedColorByKey, tags, annotationLabels],
        ([$selectedColorByType, $selectedColorByKey, $tags, $annotationLabels]): ColorBy => {
            if ($selectedColorByType === 'metadata' && $selectedColorByKey) {
                return { type: 'metadata_field', key: $selectedColorByKey };
            }

            if ($selectedColorByType === 'tags') {
                return { type: 'tag', tag_ids: $tags.map((tag) => tag.tag_id) };
            }

            if ($selectedColorByType === 'annotation_label') {
                return {
                    type: 'annotation',
                    annotation_label_ids: $annotationLabels.map(
                        (label) => label.annotation_label_id
                    )
                };
            }

            return null;
        }
    );

    return {
        colorBy,
        selectedColorByKey: readonly(selectedColorByKey),
        setSelectedColorByKey: (key) => selectedColorByKey.set(key)
    };
}
