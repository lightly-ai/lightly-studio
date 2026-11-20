import { isEqual } from 'lodash-es';
import { derived, readable, readonly, writable, type Readable } from 'svelte/store';
import type { GetEmbeddings2dRequest } from '$lib/api/lightly_studio_local/types.gen';
import type { PlotColorByType } from '../PlotColorByPopover/usePlotColorByType/usePlotColorByType';

type ColorBy = GetEmbeddings2dRequest['color_by'];

interface UsePlotColorByParams {
    selectedColorByType: Readable<PlotColorByType | null>;
    tags: Readable<{ tag_id: string }[]>;
    // undefined while the labels load.
    annotationLabels: Readable<{ annotation_label_id: string }[] | undefined>;
}

interface UsePlotColorByReturn {
    // undefined until the color-by can be sent: the plot must not fetch with partial labels.
    colorBy: Readable<ColorBy | undefined>;
    selectedColorByKey: Readable<string | null>;
    setSelectedColorByKey: (key: string | null) => void;
}

export function usePlotColorBy({
    selectedColorByType,
    tags,
    annotationLabels
}: UsePlotColorByParams): UsePlotColorByReturn {
    const selectedColorByKey = writable<string | null>(null);

    const computedColorBy = derived(
        [selectedColorByType, selectedColorByKey, tags, annotationLabels],
        ([$selectedColorByType, $selectedColorByKey, $tags, $annotationLabels]):
            | ColorBy
            | undefined => {
            if ($selectedColorByType === 'metadata' && $selectedColorByKey) {
                return { type: 'metadata_field', key: $selectedColorByKey };
            }

            if ($selectedColorByType === 'tags') {
                return { type: 'tag', tag_ids: $tags.map((tag) => tag.tag_id) };
            }

            if ($selectedColorByType === 'annotation_label') {
                if ($annotationLabels === undefined) return undefined;
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

    // The derived store emits a new object whenever any input emits, e.g. when a tag is created
    // while coloring by annotations. Consumers key effects and queries on color-by, so it only
    // emits when its content changes.
    const colorBy = readable<ColorBy | undefined>(undefined, (set) => {
        let lastColorBy: ColorBy | undefined;
        return computedColorBy.subscribe((nextColorBy) => {
            if (isEqual(nextColorBy, lastColorBy)) return;
            lastColorBy = nextColorBy;
            set(nextColorBy);
        });
    });

    return {
        colorBy,
        selectedColorByKey: readonly(selectedColorByKey),
        setSelectedColorByKey: (key) => selectedColorByKey.set(key)
    };
}
