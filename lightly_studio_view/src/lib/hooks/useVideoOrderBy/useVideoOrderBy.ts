import { derived, get, type Readable } from 'svelte/store';
import { SortDirection } from '$lib/api/lightly_studio_local';
import type { VideoSortFieldExpr } from '$lib/api/lightly_studio_local';
import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
import { usePostHog } from '$lib/hooks';
import {
    useVideoSortFields,
    type SortField
} from '$lib/hooks/useVideoSortFields/useVideoSortFields';

interface UseVideoOrderByParams {
    collectionId: () => string;
}

interface UseVideoOrderByReturn {
    allSortFields: Readable<SortField[]>;
    selectedDirection: Readable<SortDirection>;
    selectedLabel: Readable<string | null>;
    isFieldSelected: Readable<(field: SortField) => boolean>;
    handleFieldClick: (field: SortField) => void;
    toggleDirection: () => void;
}

function checkIsFieldSelected(field: SortField, current: VideoSortFieldExpr | undefined): boolean {
    if (!current) return false;
    return current.field_name === field.value && current.source === field.source;
}

function sortExprAnalytics(expr: VideoSortFieldExpr): { sort_source: string; field_name: string } {
    return {
        sort_source: expr.source === 'metadata' ? 'metadata_field' : 'video_field',
        field_name: expr.field_name
    };
}

export function useVideoOrderBy({ collectionId }: UseVideoOrderByParams): UseVideoOrderByReturn {
    const { videoSortBy, updateSortBy } = useVideoFilters();
    const { allSortFields } = useVideoSortFields();
    const { trackEvent } = usePostHog();

    const selectedDirection = derived(
        videoSortBy,
        ($videoSortBy) => $videoSortBy?.[0]?.direction ?? SortDirection.ASC
    );

    const selectedLabel = derived(
        [videoSortBy, allSortFields],
        ([$videoSortBy, $allSortFields]) => {
            const current = $videoSortBy?.[0];
            if (!current) return null;
            return (
                $allSortFields.find(
                    (field) => field.source === current.source && field.value === current.field_name
                )?.label ?? null
            );
        }
    );

    // Returns a checker function so the template can call $isFieldSelected(field)
    // and reactively update when videoSortBy changes.
    const isFieldSelected = derived(
        videoSortBy,
        ($videoSortBy) =>
            (field: SortField): boolean =>
                checkIsFieldSelected(field, $videoSortBy?.[0])
    );

    function handleFieldClick(field: SortField) {
        const current = get(videoSortBy)?.[0];
        if (checkIsFieldSelected(field, current)) {
            updateSortBy(null);
            return;
        }
        const direction = get(selectedDirection);
        const next: VideoSortFieldExpr = {
            source: field.source,
            field_name: field.value,
            direction
        };
        updateSortBy([next]);
        const { sort_source, field_name } = sortExprAnalytics(next);
        trackEvent('grid_sorted', {
            collection_id: collectionId(),
            sort_source,
            field_name,
            direction
        });
    }

    function toggleDirection() {
        const current = get(videoSortBy)?.[0];
        if (!current) return;
        const direction =
            get(selectedDirection) === SortDirection.ASC ? SortDirection.DESC : SortDirection.ASC;
        const next: VideoSortFieldExpr = { ...current, direction };
        updateSortBy([next]);
        const { sort_source, field_name } = sortExprAnalytics(next);
        trackEvent('grid_sorted', {
            collection_id: collectionId(),
            sort_source,
            field_name,
            direction
        });
    }

    return {
        allSortFields,
        selectedDirection,
        selectedLabel,
        isFieldSelected,
        handleFieldClick,
        toggleDirection
    };
}
