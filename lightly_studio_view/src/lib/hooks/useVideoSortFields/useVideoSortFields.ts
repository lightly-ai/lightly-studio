import { derived, type Readable } from 'svelte/store';
import type { VideoSortFieldExpr } from '$lib/api/lightly_studio_local';
import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';

export interface ColumnSortField {
    source: VideoSortFieldExpr['source'];
    value: string;
    label: string;
}

export type SortField = ColumnSortField;

interface UseVideoSortFieldsReturn {
    allSortFields: Readable<SortField[]>;
}

// Videos have no evaluation metrics, so the field list is the plain columns plus
// every sortable metadata key. The `value`s are the backend sort field names
// (see query_translation._SORT_FIELDS).
export const VIDEO_SORT_FIELDS: ColumnSortField[] = [
    { source: 'video', value: 'file_name', label: 'file name' },
    { source: 'video', value: 'file_path_abs', label: 'file path' },
    { source: 'video', value: 'created_at', label: 'created at' },
    { source: 'video', value: 'width', label: 'width' },
    { source: 'video', value: 'height', label: 'height' },
    { source: 'video', value: 'duration_s', label: 'duration' },
    { source: 'video', value: 'fps', label: 'frame rate' }
];

export function useVideoSortFields(): UseVideoSortFieldsReturn {
    const { metadataInfo } = useMetadataFilters();

    const metadataSortFields = derived(metadataInfo, ($metadataInfo) =>
        ($metadataInfo ?? [])
            .filter((info) => ['integer', 'float', 'string', 'boolean'].includes(info.type))
            .map(
                (info): ColumnSortField => ({
                    source: 'metadata' as VideoSortFieldExpr['source'],
                    value: info.name,
                    label: `metadata.${info.name}`
                })
            )
    );

    const allSortFields = derived(metadataSortFields, ($metadataSortFields) => [
        ...VIDEO_SORT_FIELDS,
        ...$metadataSortFields
    ]);

    return { allSortFields };
}
