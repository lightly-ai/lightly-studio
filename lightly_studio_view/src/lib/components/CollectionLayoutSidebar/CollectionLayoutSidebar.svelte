<script lang="ts">
    import { LabelsMenu, TagsMenu, CombinedMetadataDimensionsFilters } from '$lib/components';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { SlidersHorizontal } from '@lucide/svelte';
    import type { useRouteType } from '$lib/hooks/useRouteType/useRouteType';
    import type { GridType, Annotation } from '$lib/types';
    import type { Readable } from 'svelte/store';

    const {
        collectionId,
        gridType,
        routeType,
        annotationFilterRows,
        toggleAnnotationFilterSelection
    }: {
        collectionId: string;
        gridType: GridType;
        routeType: ReturnType<typeof useRouteType>;
        annotationFilterRows: Readable<Annotation[]>;
        toggleAnnotationFilterSelection: (labelId: string) => void;
    } = $props();
</script>

<div>
    <TagsMenu collection_id={collectionId} {gridType} />
</div>
<Segment title="Filters" icon={SlidersHorizontal}>
    <div class="space-y-2">
        <LabelsMenu
            {annotationFilterRows}
            onToggleAnnotationFilter={toggleAnnotationFilterSelection}
        />
        {#if routeType.isSamples || routeType.isVideos || routeType.isVideoFrames}
            {#key collectionId}
                <CombinedMetadataDimensionsFilters
                    isVideos={routeType.isVideos}
                    isVideoFrames={routeType.isVideoFrames}
                />
            {/key}
        {/if}
    </div>
</Segment>
