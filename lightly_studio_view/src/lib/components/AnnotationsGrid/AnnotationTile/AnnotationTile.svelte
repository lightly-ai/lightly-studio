<script lang="ts">
    import { AnnotationsGridItem, SelectableBox } from '$lib/components';
    import { GridItem } from '$lib/components/GridItem';
    import { AnnotationType, type AnnotationWithPayloadView } from '$lib/api/lightly_studio_local';
    import AnnotationClassificationGridItem from '../AnnotationClassificationGridItem/AnnotationClassificationGridItem.svelte';
    import type { CropWindow } from '../AnnotationItem/renderCropObjectUrl';
    import {
        buildAnnotationDragData,
        buildClassificationDragData
    } from '../AnnotationsGrid.helpers';

    interface Props {
        /** The annotation with its parent sample data. */
        annotation: AnnotationWithPayloadView;
        /** Position of this tile within the grid, used for shift-click range selection. */
        index: number;
        /** Width of the grid tile in pixels. */
        width: number;
        /** Height of the grid tile in pixels. */
        height: number;
        /** Positioning style forwarded to the underlying GridItem. */
        style?: string;
        /** Whether this tile is currently selected. */
        selected: boolean;
        /** Whether to show the annotation label text on the tile. */
        showLabel: boolean;
        /** Collection version cache-buster (same as AnnotationImageGridItem). */
        cachedCollectionVersion: string;
        /** Whether the current user is allowed to see the selection overlay. */
        canShowSelectionOverlay: boolean;
        /** Crop geometry reported by the tile, once available; undefined until then. */
        cropWindow: CropWindow | undefined;
        /** Rendered crop blob URL, populated lazily once a drag actually starts. */
        cropUrl: string | undefined;
        /** Reports full-image crop geometry for drag-to-search (same contract as AnnotationItem). */
        onCropWindowChange: (annotationId: string, window: CropWindow | null) => void;
        /** Fires once a drag on this tile passes the movement threshold. */
        onDragStart: (annotationId: string) => void;
        /** Fires on click or Enter/Space; `event.shiftKey` drives range selection. */
        onSelect: (event: MouseEvent | KeyboardEvent, annotationId: string, index: number) => void;
        /** Fires on double-click, navigating to the sample detail view. */
        onDoubleClick: (annotationId: string) => void;
    }

    let {
        annotation,
        index,
        width,
        height,
        style,
        selected,
        showLabel,
        cachedCollectionVersion,
        canShowSelectionOverlay,
        cropWindow,
        cropUrl,
        onCropWindowChange,
        onDragStart,
        onSelect,
        onDoubleClick
    }: Props = $props();

    const annotationId = $derived(annotation.annotation.sample_id);
    const isClassification = $derived(
        annotation.annotation.annotation_type === AnnotationType.CLASSIFICATION
    );
    const dragData = $derived(
        isClassification
            ? buildClassificationDragData({
                  annotation: annotation.annotation,
                  cropWindow,
                  cropUrl
              })
            : buildAnnotationDragData({ annotation: annotation.annotation, cropWindow, cropUrl })
    );
</script>

{#key annotationId}
    <GridItem
        {width}
        {height}
        {style}
        dataTestId="annotation-grid-item"
        tag={false}
        ariaLabel={`Edit annotation: ${annotationId}`}
        {dragData}
        onDragStart={() => onDragStart(annotationId)}
        onSelect={(event) => onSelect(event, annotationId, index)}
        ondblclick={() => onDoubleClick(annotationId)}
    >
        <div
            class="annotation-grid-item relative h-full w-full"
            data-annotation-id={annotationId}
            data-annotation-index={index}
            data-sample-id={annotation.annotation.parent_sample_id}
            data-index={index}
        >
            {#if canShowSelectionOverlay && selected}
                <div class="pointer-events-none absolute right-2 top-1.5 z-10" inert>
                    <SelectableBox onSelect={() => undefined} isSelected={true} />
                </div>
            {/if}

            {#if isClassification}
                <!-- One classification annotation = one tile (1:1 mapping, same as OD/seg). -->
                <AnnotationClassificationGridItem
                    {annotation}
                    containerWidth={width}
                    containerHeight={height}
                    {selected}
                    {cachedCollectionVersion}
                    {onCropWindowChange}
                />
            {:else}
                <AnnotationsGridItem
                    {annotation}
                    {width}
                    {height}
                    {cachedCollectionVersion}
                    {showLabel}
                    {selected}
                    {onCropWindowChange}
                />
            {/if}
        </div>
    </GridItem>
{/key}
