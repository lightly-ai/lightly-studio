<script lang="ts">
    import { Card, CardContent, Segment, Spinner } from '$lib/components';
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL } from '$env/static/public';
    import type { PageData } from '../[sampleId]/$types';
    import { type AnnotationView, type SampleView, type VideoFrameView } from '$lib/api/lightly_studio_local';
    import ZoomableContainer from '$lib/components/ZoomableContainer/ZoomableContainer.svelte';
    import type { Writable } from 'svelte/store';
    import type { FrameAdjacents } from '$lib/hooks/useFramesAdjacents/useFramesAdjacents';
    import SteppingNavigation from '$lib/components/SteppingNavigation/SteppingNavigation.svelte';
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import FrameDetailsBreadcrumb from '$lib/components/FrameDetailsBreadcrumb/FrameDetailsBreadcrumb.svelte';
    import { Separator } from '$lib/components/ui/separator';
    import type { BoundingBox } from '$lib/types';
    import { type D3DragEvent, drag } from 'd3-drag';
    import { select } from 'd3-selection';
    import type { ListItem } from '$lib/components/SelectList/types';
    import _ from 'lodash';
    import SampleDetailsAnnotation from '$lib/components/SampleDetails/SampleDetailsAnnotation/SampleDetailsAnnotation.svelte';
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import ResizableRectangle from '$lib/components/ResizableRectangle/ResizableRectangle.svelte';
    import { page } from '$app/state';
    import { getColorByLabel } from '$lib/utils';
    import FrameAnnotationsPanel from '$lib/components/FrameAnnotationsPanel/FrameAnnotationsPanel.svelte';
    import { useDeleteAnnotation } from '$lib/hooks/useDeleteAnnotation/useDeleteAnnotation';
    import { toast } from 'svelte-sonner';
    import { useFrame } from '$lib/hooks/useFrame/useFrame';
    import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
    import { useCreateLabel } from '$lib/hooks/useCreateLabel/useCreateLabel';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';

    const { data }: { data: PageData } = $props();
    const {
        frameIndex,
        frameAdjacents,
        datasetId,
        sampleId
    }: {
        sample: VideoFrameView;
        frameIndex: number | null;
        frameAdjacents: Writable<FrameAdjacents> | null;
        datasetId: string;
        sampleId: string;
    } = $derived(data);
    const { refetch, videoFrame } = $derived(useFrame(sampleId));

    const sample = $derived($videoFrame.data);

    let boundingBox = $state<BoundingBox | undefined>();
    let isDragging = $state(false);
    let temporaryBbox = $state<BoundingBox | null>(null);
    let interactionRect: SVGRectElement | null = $state(null);
    let mousePosition = $state<{ x: number; y: number } | null>(null);
    let addAnnotationEnabled = $state(false);
    let addAnnotationLabel = $state<ListItem | undefined>({ value: 'Opa', label: 'Opa' });
    let annotationsToShow = $state<AnnotationView[]>([]);
    let annotationsIdsToHide = $state<Set<string>>(new Set());
    const { isEditingMode } = page.data.globalStorage;
    let isPanModeEnabled = $state(false);
    const isResizable = $derived($isEditingMode && !isPanModeEnabled);
    let selectedAnnotationId = $state<string>();
    const { createAnnotation } = useCreateAnnotation({
        datasetId: data.dataset.dataset_id
    });

    const labels = useAnnotationLabels();
    const { createLabel } = useCreateLabel();

    const actualAnnotationsToShow = $derived.by(() => {
        return annotationsToShow.filter(
            (annotation: AnnotationView) => !annotationsIdsToHide.has(annotation.annotation_id)
        );
    });
    const { isHidden, handleKeyEvent } = useHideAnnotations();
    const { deleteAnnotation } = useDeleteAnnotation({
        datasetId
    });

    const drawerStrokeColor = $derived(
        addAnnotationLabel ? getColorByLabel(addAnnotationLabel.label, 1).color : 'blue'
    );

    const isDrawingEnabled = $derived(
        addAnnotationEnabled && !isPanModeEnabled && addAnnotationLabel !== undefined
    );

    type D3Event = D3DragEvent<SVGRectElement, unknown, unknown>;

    const trackMousePositionOrig = (event: MouseEvent) => {
        if (!interactionRect || isDragging || !sample) return;

        const svgRect = interactionRect.getBoundingClientRect();
        const clientX = event.clientX;
        const clientY = event.clientY;
        const x = ((clientX - svgRect.left) / svgRect.width) * sample.video.width;
        const y = ((clientY - svgRect.top) / svgRect.height) * sample.video.height;

        mousePosition = { x, y };
        event.stopPropagation();
        event.preventDefault();
    };

    const trackMousePosition = _.throttle(trackMousePositionOrig, 50);

    const BOX_MIN_SIZE_PX = 10;

    function goToNextFrame() {
        if (frameIndex == null || !sample) return null;
        if (!frameAdjacents) return null;

        const sampleNext = $frameAdjacents?.sampleNext;
        if (!sampleNext) return null;

        goto(
            routeHelpers.toFramesDetails(
                (sample.sample as SampleView).dataset_id,
                sampleNext.sample_id,
                frameIndex + 1
            )
        );
    }

    function goToPreviousFrame() {
        if (frameIndex == null || !sample) return null;
        if (!frameAdjacents) return null;

        const samplePrevious = $frameAdjacents?.samplePrevious;
        if (!samplePrevious) return null;

        goto(
            routeHelpers.toFramesDetails(
                (sample.sample as SampleView).dataset_id,
                samplePrevious.sample_id,
                frameIndex - 1
            )
        );
    }

    const cancelDrag = () => {
        isDragging = false;
        temporaryBbox = null;
        mousePosition = null;
    };

    $effect(() => {
        setupDragBehavior();
        console.log({ temporaryBbox, isDragging, addAnnotationLabel });
    });

    const setupDragBehavior = () => {
        if (!interactionRect) return;

        const rectSelection = select(interactionRect);

        let startPoint: { x: number; y: number } | null = null;

        // Setup D3 drag behavior for annotation creation
        const dragBehavior = drag<SVGRectElement, unknown>()
            .on('start', (event: D3Event) => {
                if (!addAnnotationEnabled || !sample) return;
                isDragging = true;
                // Get mouse position relative to the SVG element
                const svgRect = interactionRect!.getBoundingClientRect();
                const clientX = event.sourceEvent.clientX;
                const clientY = event.sourceEvent.clientY;
                const x = ((clientX - svgRect.left) / svgRect.width) * sample.video.width;
                const y = ((clientY - svgRect.top) / svgRect.height) * sample.video.height;

                startPoint = { x, y };
                temporaryBbox = { x, y, width: 0, height: 0 };
                mousePosition = { x, y };
            })
            .on('drag', (event: D3Event) => {
                if (!temporaryBbox || !isDragging || !startPoint || !sample) return;
                // Get current mouse position relative to the SVG element
                const svgRect = interactionRect!.getBoundingClientRect();
                const clientX = event.sourceEvent.clientX;
                const clientY = event.sourceEvent.clientY;
                let currentX = ((clientX - svgRect.left) / svgRect.width) * sample.video.width;
                let currentY = ((clientY - svgRect.top) / svgRect.height) * sample.video.height;

                // Constrain current position to image bounds
                const imageWidth = sample.video.width;
                const imageHeight = sample.video.height;
                currentX = Math.max(0, Math.min(currentX, imageWidth));
                currentY = Math.max(0, Math.min(currentY, imageHeight));

                const x = Math.min(startPoint.x, currentX);
                const y = Math.min(startPoint.y, currentY);
                const width = Math.abs(currentX - startPoint.x);
                const height = Math.abs(currentY - startPoint.y);

                temporaryBbox = { x, y, width, height };
                mousePosition = { x: currentX, y: currentY };
            })
            .on('end', () => {
                if (!temporaryBbox || !isDragging) return;

                // Only create annotation if the rectangle has meaningful size (> 10px in both dimensions)
                if (
                    temporaryBbox.width > BOX_MIN_SIZE_PX &&
                    temporaryBbox.height > BOX_MIN_SIZE_PX
                ) {
                    if (addAnnotationLabel) {
                        // createObjectDetectionAnnotation({
                        //     x: temporaryBbox.x,
                        //     y: temporaryBbox.y,
                        //     width: temporaryBbox.width,
                        //     height: temporaryBbox.height,
                        //     labelName: addAnnotationLabel.label
                        // });
                    }
                }

                cancelDrag();
                startPoint = null;
            });

        rectSelection.call(dragBehavior);

        rectSelection.on('mousemove', trackMousePosition);

        // Return cleanup function
        return () => {
            dragBehavior.on('start', null).on('drag', null).on('end', null);
        };
    };

    const toggleAnnotationSelection = (annotationId: string) => {
        if (isPanModeEnabled) return;

        if (selectedAnnotationId === annotationId) {
            selectedAnnotationId = undefined;
        } else {
            selectedAnnotationId = annotationId;
        }
    };

    const onToggleShowAnnotation = (annotationId: string) => {
        const newSet = new Set(annotationsIdsToHide);
        if (newSet.has(annotationId)) {
            newSet.delete(annotationId);
        } else {
            newSet.add(annotationId);
        }
        annotationsIdsToHide = newSet;
    };

    const handleDeleteAnnotation = async (annotationId: string) => {
        const _delete = async () => {
            try {
                await deleteAnnotation(annotationId);
                toast.success('Annotation deleted successfully');
                refetch();
                if (selectedAnnotationId === annotationId) {
                    selectedAnnotationId = undefined;
                }
            } catch (error) {
                toast.error('Failed to delete annotation. Please try again.');
                console.error('Error deleting annotation:', error);
            }
        };
        _delete();
    };

    const createObjectDetectionAnnotation = async ({
        x,
        y,
        width,
        height,
        labelName
    }: {
        x: number;
        y: number;
        width: number;
        height: number;
        labelName: string;
    }) => {
        if (!$labels.data) {
            return;
        }

        let label = $labels.data.find((label) => label.annotation_label_name === labelName);

        // Create label if it does not exist yet
        if (!label) {
            label = await createLabel({
                annotation_label_name: labelName
            });
        }

        try {
            const newAnnotation = await createAnnotation({
                parent_sample_id: sampleId,
                annotation_type: 'object_detection',
                x: Math.round(x),
                y: Math.round(y),
                width: Math.round(width),
                height: Math.round(height),
                annotation_label_id: label.annotation_label_id!
            });

            refetch();

            selectedAnnotationId = newAnnotation.annotation_id;

            toast.success('Annotation created successfully');
            return newAnnotation;
        } catch (error) {
            toast.error('Failed to create annotation. Please try again.');
            console.error('Error creating annotation:', error);
            return;
        }
    };
</script>

<div class="flex h-full w-full flex-col space-y-4">
    <div class="flex w-full items-center">
        <FrameDetailsBreadcrumb dataset={data.dataset} {frameIndex} />
    </div>
    <Separator class="bg-border-hard mb-4" />
    {#if sample}
        <div class="flex min-h-0 flex-1 gap-4">
            <Card className="flex flex-col w-[60vw]">
                <CardContent className="flex flex-col gap-4 overflow-hidden h-full">
                    <div class="relative h-full w-full overflow-hidden">
                        {#if frameAdjacents}
                            <SteppingNavigation
                                hasPrevious={!!$frameAdjacents?.samplePrevious}
                                hasNext={!!$frameAdjacents?.sampleNext}
                                onPrevious={goToPreviousFrame}
                                onNext={goToNextFrame}
                            />
                        {/if}
                        <ZoomableContainer
                            {boundingBox}
                            width={sample.video.width}
                            height={sample.video.height}
                        >
                            {#snippet zoomableContent()}
                                <image
                                    width="100%"
                                    height="100%"
                                    href={`${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${sample.sample_id}`}
                                />
                                <g class:invisible={$isHidden}>
                                    {#each actualAnnotationsToShow as annotation (annotation.annotation_id)}
                                        <SampleDetailsAnnotation
                                            annotationId={annotation.annotation_id}
                                            sampleId={sample.sample_id}
                                            {datasetId}
                                            {isResizable}
                                            isSelected={selectedAnnotationId ===
                                                annotation.annotation_id}
                                            {toggleAnnotationSelection}
                                        />
                                    {/each}

                                    {#if temporaryBbox && isDragging && addAnnotationLabel}
                                        <ResizableRectangle
                                            bbox={temporaryBbox}
                                            colorStroke={drawerStrokeColor}
                                            colorFill="rgba(0, 123, 255, 0.1)"
                                            style="outline: 0;"
                                            opacity={0.8}
                                            scale={1}
                                        />
                                    {/if}

                                    {#if mousePosition && isDrawingEnabled}
                                        <!-- Horizontal crosshair line -->
                                        <line
                                            x1="0"
                                            y1={mousePosition.y}
                                            x2={sample.video.width}
                                            y2={mousePosition.y}
                                            stroke={drawerStrokeColor}
                                            stroke-width="1"
                                            vector-effect="non-scaling-stroke"
                                            stroke-dasharray="5,5"
                                            opacity="0.6"
                                        />
                                        <!-- Vertical crosshair line -->
                                        <line
                                            x1={mousePosition.x}
                                            y1="0"
                                            x2={mousePosition.x}
                                            y2={sample.video.height}
                                            vector-effect="non-scaling-stroke"
                                            stroke={drawerStrokeColor}
                                            stroke-width="1"
                                            stroke-dasharray="5,5"
                                            opacity="0.6"
                                        />
                                    {/if}
                                </g>
                                {#if isDrawingEnabled}
                                    <rect
                                        bind:this={interactionRect}
                                        width={sample.video.width}
                                        height={sample.video.height}
                                        class="select-none"
                                        fill="transparent"
                                        role="button"
                                        style="outline: 0;cursor: crosshair;"
                                        tabindex="0"
                                    />
                                {/if}
                            {/snippet}
                        </ZoomableContainer>
                    </div>
                </CardContent>
            </Card>

            <Card className="flex flex-col flex-1 overflow-hidden">
                <CardContent className="h-full overflow-y-auto">
                    <Segment title="Video frame details">
                        <div class="text-diffuse-foreground min-w-full space-y-3">
                            <div class="flex items-start gap-3">
                                <span class="truncate text-sm font-medium" title="Width"
                                    >Number:</span
                                >
                                <span class="text-sm">{sample.frame_number}</span>
                            </div>
                            <div class="flex items-start gap-3">
                                <span class="truncate text-sm font-medium" title="Height"
                                    >Timestamp:</span
                                >
                                <span class="text-sm"
                                    >{sample.frame_timestamp_s.toFixed(2)} seconds</span
                                >
                            </div>
                            <div class="flex items-start gap-3">
                                <span class="text-sm font-medium" title="Height"
                                    >Video file path:</span
                                >
                                <span class="w-auto break-all text-sm"
                                    >{sample.video.file_path_abs}</span
                                >
                            </div>
                        </div>
                    </Segment>
                    <FrameAnnotationsPanel
                        bind:addAnnotationEnabled
                        bind:addAnnotationLabel
                        {annotationsIdsToHide}
                        {selectedAnnotationId}
                        onAnnotationClick={toggleAnnotationSelection}
                        {onToggleShowAnnotation}
                        onDeleteAnnotation={handleDeleteAnnotation}
                        onUpdate={refetch}
                    />
                </CardContent>
            </Card>
        </div>
    {:else if $videoFrame.isLoading}
        <div class="flex h-screen items-center justify-center">
            <Spinner />
        </div>
    {/if}
</div>
