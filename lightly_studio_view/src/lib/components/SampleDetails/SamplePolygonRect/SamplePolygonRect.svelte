<script lang="ts">
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useSelectClassDialog } from '$lib/hooks/useSelectClassDialog/useSelectClassDialog';
    import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
    import { useCreateLabel } from '$lib/hooks/useCreateLabel/useCreateLabel';
    import { toast } from 'svelte-sonner';
    import { onDestroy } from 'svelte';
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { useCollectionWithChildren } from '$lib/hooks/useCollection/useCollection';
    import { page } from '$app/state';
    import { addAnnotationCreateToUndoStack } from '$lib/services/addAnnotationCreateToUndoStack';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useDeleteAnnotation } from '$lib/hooks/useDeleteAnnotation/useDeleteAnnotation';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import SelectClassDialog from '$lib/components/SelectClassDialog/SelectClassDialog.svelte';
    import SampleAnnotationRect from '../SampleAnnotationRect/SampleAnnotationRect.svelte';

    type SamplePolygonRectProps = {
        sample: {
            width: number;
            height: number;
            annotations: AnnotationView[];
        };
        interactionRect?: SVGRectElement | undefined | null;
        sampleId: string;
        collectionId: string;
        drawerStrokeColor: string;
        refetch: () => void;
    };

    let {
        sample,
        interactionRect = $bindable<SVGRectElement>(),
        collectionId,
        refetch,
        sampleId,
        drawerStrokeColor
    }: SamplePolygonRectProps = $props();

    // Draft polygon state
    let draftPoints = $state<Array<[number, number]>>([]);
    let cursorPoint = $state<[number, number] | null>(null);

    const CLOSE_THRESHOLD_SCREEN_PX = 12;
    const MIN_POINTS = 3;

    const labels = useAnnotationLabels(() => ({ collectionId }));

    const {
        open: showSelectClassDialog,
        requestLabel,
        handleConfirm: handleClassSelected,
        handleCancel: handleClassDialogCancel
    } = useSelectClassDialog();

    const { createLabel } = useCreateLabel({ collectionId });
    const { createAnnotation } = useCreateAnnotation({ collectionId });
    const { deleteAnnotation } = useDeleteAnnotation({ collectionId });
    const { addReversibleAction, updateLastAnnotationLabel } = useGlobalStorage();

    const datasetId = $derived(page.params.dataset_id!);
    const { refetch: refetchRootCollection } = $derived.by(() =>
        useCollectionWithChildren({ collectionId: datasetId })
    );

    const {
        context: annotationLabelContext,
        setLastCreatedAnnotationId,
        setAnnotationId,
        setIsDrawing,
        setAnnotationLabel
    } = useAnnotationLabelContext();

    const getImageCoords = (clientX: number, clientY: number): [number, number] | null => {
        if (!interactionRect) return null;

        const svgRect = interactionRect.getBoundingClientRect();
        const x = ((clientX - svgRect.left) / svgRect.width) * sample.width;
        const y = ((clientY - svgRect.top) / svgRect.height) * sample.height;

        const clampedX = Math.max(0, Math.min(x, sample.width));
        const clampedY = Math.max(0, Math.min(y, sample.height));

        return [clampedX, clampedY];
    };

    const isNearFirstPoint = (clientX: number, clientY: number): boolean => {
        if (draftPoints.length < MIN_POINTS || !interactionRect) return false;

        const svgRect = interactionRect.getBoundingClientRect();
        const scaleX = svgRect.width / sample.width;
        const scaleY = svgRect.height / sample.height;

        const firstScreenX = draftPoints[0][0] * scaleX + svgRect.left;
        const firstScreenY = draftPoints[0][1] * scaleY + svgRect.top;

        const dx = clientX - firstScreenX;
        const dy = clientY - firstScreenY;

        return Math.sqrt(dx * dx + dy * dy) < CLOSE_THRESHOLD_SCREEN_PX;
    };

    const handlePointerMove = (event: PointerEvent) => {
        const coords = getImageCoords(event.clientX, event.clientY);
        cursorPoint = coords;
    };

    const handlePointerLeave = () => {
        cursorPoint = null;
    };

    const handleClick = (event: MouseEvent) => {
        // On double-click (detail=2), finish the polygon without adding another point
        if (event.detail === 2) {
            if (draftPoints.length >= MIN_POINTS) {
                finishPolygon();
            }
            return;
        }

        const coords = getImageCoords(event.clientX, event.clientY);
        if (!coords) return;

        // Close polygon if clicking near first point
        if (isNearFirstPoint(event.clientX, event.clientY)) {
            finishPolygon();
            return;
        }

        if (draftPoints.length === 0) {
            setIsDrawing(true);
        }

        draftPoints = [...draftPoints, coords];
    };

    const cancelPolygon = () => {
        draftPoints = [];
        cursorPoint = null;
        setIsDrawing(false);
    };

    const handleKeyDown = (event: KeyboardEvent) => {
        if (event.key === 'Escape') {
            event.preventDefault();
            cancelPolygon();
        } else if (event.key === 'Enter') {
            event.preventDefault();
            if (draftPoints.length >= MIN_POINTS) {
                finishPolygon();
            }
        }
    };

    const finishPolygon = async () => {
        if (draftPoints.length < MIN_POINTS) {
            toast.error('A polygon requires at least 3 points.');
            return;
        }

        const points = draftPoints.slice();
        cancelPolygon();

        try {
            let selectedLabelName = annotationLabelContext.annotationLabel;
            if (!selectedLabelName) {
                const result = await requestLabel();
                if (!result?.label) {
                    toast.error('Please select a class before creating an annotation');
                    return;
                }
                selectedLabelName = result.label;
                setAnnotationLabel(selectedLabelName);
                updateLastAnnotationLabel(collectionId, selectedLabelName);
            }

            let label = labels.data?.find(
                (l) => l.annotation_label_name === selectedLabelName
            );

            if (!label) {
                label = await createLabel({
                    dataset_id: datasetId,
                    annotation_label_name: selectedLabelName
                });
            }

            const newAnnotation = await createAnnotation({
                parent_sample_id: sampleId,
                annotation_type: 'polygon',
                annotation_label_id: label.annotation_label_id!,
                annotation_collection_name: annotationLabelContext.annotationSource ?? undefined,
                points: points.map(([x, y]) => [Math.round(x), Math.round(y)])
            });

            if (sample.annotations.length === 0) {
                refetchRootCollection();
            }

            addAnnotationCreateToUndoStack({
                annotation: newAnnotation,
                addReversibleAction,
                deleteAnnotation,
                refetch,
                onDelete: () => setAnnotationId(null)
            });

            refetch();

            setLastCreatedAnnotationId(newAnnotation.sample_id);
            setAnnotationId(newAnnotation.sample_id);

            toast.success('Annotation created successfully');
        } catch (error) {
            toast.error('Failed to create annotation. Please try again.');
            console.error('Error creating polygon annotation:', error);
        }
    };

    onDestroy(() => {
        cancelPolygon();
        handleClassDialogCancel();
    });

    // Cancel draft when user switches away from polygon tool
    $effect(() => {
        if (!annotationLabelContext.annotationType || annotationLabelContext.annotationType !== 'polygon') {
            cancelPolygon();
        }
    });

    const vertexRadius = $derived.by(() => {
        if (!interactionRect) return 4;
        const svgRect = interactionRect.getBoundingClientRect();
        // Keep vertex markers a consistent screen size (~5px) regardless of image scale
        return 5 / (svgRect.width / sample.width);
    });
</script>

{#if draftPoints.length > 0}
    <!-- Preview polygon fill when at least 3 points -->
    {#if draftPoints.length >= MIN_POINTS}
        <polygon
            points={draftPoints.map(([x, y]) => `${x},${y}`).join(' ')}
            fill={drawerStrokeColor}
            fill-opacity="0.15"
            stroke="none"
            pointer-events="none"
        />
    {/if}

    <!-- Polygon outline connecting existing points -->
    <polyline
        points={[...draftPoints, ...(cursorPoint ? [cursorPoint] : [])].map(([x, y]) => `${x},${y}`).join(' ')}
        fill="none"
        stroke={drawerStrokeColor}
        stroke-width="1"
        vector-effect="non-scaling-stroke"
        stroke-dasharray="4,3"
        opacity="0.9"
        pointer-events="none"
    />

    <!-- Closing line from cursor back to first point when near enough to close -->
    {#if cursorPoint && draftPoints.length >= MIN_POINTS}
        <line
            x1={cursorPoint[0]}
            y1={cursorPoint[1]}
            x2={draftPoints[0][0]}
            y2={draftPoints[0][1]}
            stroke={drawerStrokeColor}
            stroke-width="1"
            vector-effect="non-scaling-stroke"
            stroke-dasharray="2,3"
            opacity="0.5"
            pointer-events="none"
        />
    {/if}

    <!-- Vertex markers -->
    {#each draftPoints as [x, y], i}
        <circle
            cx={x}
            cy={y}
            r={vertexRadius}
            fill={i === 0 && draftPoints.length >= MIN_POINTS ? drawerStrokeColor : 'white'}
            stroke={drawerStrokeColor}
            stroke-width="1"
            vector-effect="non-scaling-stroke"
            pointer-events="none"
        />
    {/each}
{/if}

<SampleAnnotationRect
    bind:interactionRect
    cursor={'crosshair'}
    {sample}
    onclick={handleClick}
    onpointermove={handlePointerMove}
    onpointerleave={handlePointerLeave}
    onkeydown={handleKeyDown}
/>

<SelectClassDialog
    bind:open={$showSelectClassDialog}
    labels={labels.data?.map((l) => l.annotation_label_name ?? '').filter(Boolean) ?? []}
    onConfirm={handleClassSelected}
    onCancel={handleClassDialogCancel}
/>
