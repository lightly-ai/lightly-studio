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
        annotation: AnnotationWithPayloadView;
        index: number;
        width: number;
        height: number;
        style?: string;
        selected: boolean;
        showLabel: boolean;
        cachedCollectionVersion: string;
        /** Whether the current user is allowed to see the selection overlay. */
        canShowSelectionOverlay: boolean;
        cropWindow: CropWindow | undefined;
        cropUrl: string | undefined;
        onCropWindowChange: (annotationId: string, window: CropWindow | null) => void;
        onDragStart: (annotationId: string) => void;
        onSelect: (event: MouseEvent | KeyboardEvent, annotationId: string, index: number) => void;
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
