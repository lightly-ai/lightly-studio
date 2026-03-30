<script lang="ts">
    import type { AnnotationUpdateInput, AnnotationView, ImageView } from '$lib/api/lightly_studio_local';
    import {
        getAnnotationOptions,
        readAnnotationLabelsOptions,
        readImageOptions
    } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
    import {
        decodeRLEToBinaryMask,
        getImageCoordsFromMouse,
        interpolateLineBetweenPoints
    } from '$lib/components/SampleAnnotation/utils';
    import parseColor from '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/parseColor';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useInstanceSegmentationBrush } from '$lib/hooks/useInstanceSegmentationBrush';
    import {
        createSlicMaskForLabels,
        extractCellMask,
        getLabelAtPoint,
        loadSuperpixelsForImage,
        maskToColoredDataUrl,
        upsampleCellMask,
        type SlicResult,
    } from '$lib/utils/slic';
    import { useCollectionWithChildren } from '$lib/hooks/useCollection/useCollection';
    import { page } from '$app/state';
    import { useQueryClient } from '@tanstack/svelte-query';
    import { useAnnotationCountsQueryKey } from '$lib/hooks/useAnnotationCounts/useAnnotationCounts';
    import SampleAnnotationRect from '../SampleAnnotationRect/SampleAnnotationRect.svelte';

    type SampleSlicRectProps = {
        sample: {
            width: number;
            height: number;
            annotations: AnnotationView[];
        };
        interactionRect?: SVGRectElement | undefined | null;
        sampleId: string;
        collectionId: string;
        drawerStrokeColor: string;
        imageUrl: string;
        refetch: () => void;
    };

    let {
        sample,
        interactionRect = $bindable<SVGRectElement>(),
        sampleId,
        collectionId,
        drawerStrokeColor,
        imageUrl,
        refetch
    }: SampleSlicRectProps = $props();

    const labels = useAnnotationLabels({ collectionId });
    const queryClient = useQueryClient();
    const datasetId = $derived(page.params.dataset_id!);
    const { refetch: refetchRootCollection } = $derived.by(() =>
        useCollectionWithChildren({ collectionId: datasetId })
    );
    const {
        context: annotationLabelContext,
        setAnnotationId,
        setIsDrawing
    } = useAnnotationLabelContext();
    const { context: sampleDetailsToolbarContext, setSlicStatus } = useSampleDetailsToolbarContext();

    const activeAnnotationId = $derived.by(() => {
        if (annotationLabelContext.annotationId) return annotationLabelContext.annotationId;

        if (annotationLabelContext.isOnAnnotationDetailsView) {
            return sample.annotations[0]?.sample_id ?? null;
        }

        return null;
    });
    const annotationApi = $derived.by(() => {
        if (!activeAnnotationId) return null;

        return useAnnotation({
            collectionId,
            annotationId: activeAnnotationId
        });
    });
    const brushApi = $derived.by(() =>
        useInstanceSegmentationBrush({
            collectionId,
            sampleId,
            sample,
            annotations: sample.annotations,
            segmentationMode: 'instance',
            refetch,
            onAnnotationCreated: () => {
                if (sample.annotations.length === 0) {
                    refetchRootCollection();
                }
            }
        })
    );

    let slicResult = $state<SlicResult | null>(null);
    let hoveredLabel = $state<number | null>(null);
    let hoverMaskDataUrl = $state('');
    let boundaryDataUrl = $state('');
    let localMask = $state<Uint8Array | null>(null);
    let strokeMaskDataUrl = $state('');
    let committedMaskDataUrl = $state('');
    let localAnnotation = $state<AnnotationView | null>(null);
    let isPersisting = $state(false);
    let hasLocalChanges = $state(false);
    let pendingServerSync = $state(false);
    let pendingServerSyncAnnotationId = $state<string | null>(null);
    let pendingServerSyncMask = $state<number[] | null>(null);
    let isStrokeActive = $state(false);
    let strokeTouchedLabels = $state<Set<number>>(new Set());
    let strokeMode = $state<'add' | 'erase' | null>(null);
    let lastStrokePoint = $state<{ x: number; y: number } | null>(null);
    let slicLoadKey = $state<string | null>(null);
    let hoverMaskCache = new Map<number, string>();
    let upsampledMaskCache = new Map<number, Uint8Array>();

    const parsedColor = $derived(parseColor(drawerStrokeColor));
    const boundaryColor = $derived([
        parsedColor.r,
        parsedColor.g,
        parsedColor.b,
        170
    ] as [number, number, number, number]);
    const hoverColor = $derived([
        parsedColor.r,
        parsedColor.g,
        parsedColor.b,
        85
    ] as [number, number, number, number]);
    const updateAnnotation = async (input: AnnotationUpdateInput) => {
        await annotationApi?.updateAnnotation(input);
    };

    const areMasksEqual = (left: number[] | null | undefined, right: number[] | null | undefined) => {
        if (!left || !right) return false;
        if (left.length !== right.length) return false;

        for (let index = 0; index < left.length; index++) {
            if (left[index] !== right[index]) {
                return false;
            }
        }

        return true;
    };

    const refreshAnnotations = async (persistedAnnotation: AnnotationView) => {
        const imageQueryKey = readImageOptions({
            path: { sample_id: sampleId }
        }).queryKey;
        const annotationQueryKey = getAnnotationOptions({
            path: {
                annotation_id: persistedAnnotation.sample_id,
                collection_id: collectionId
            }
        }).queryKey;
        const annotationLabelsQueryKey = readAnnotationLabelsOptions({
            path: { collection_id: collectionId }
        }).queryKey;

        queryClient.setQueryData(imageQueryKey, (current: ImageView | undefined) => {
            if (!current || current.annotations.some((annotation) => annotation.sample_id === persistedAnnotation.sample_id)) {
                return current;
            }

            return {
                ...current,
                annotations: [
                    ...current.annotations,
                    {
                        ...persistedAnnotation,
                        segmentation_details: null
                    }
                ]
            };
        });

        await Promise.all([
            queryClient.invalidateQueries({
                queryKey: annotationLabelsQueryKey
            }),
            queryClient.invalidateQueries({
                queryKey: useAnnotationCountsQueryKey
            })
        ]);

        window.setTimeout(() => {
            void queryClient.invalidateQueries({
                queryKey: imageQueryKey
            });
            void queryClient.invalidateQueries({
                queryKey: annotationQueryKey
            });
        }, 0);
    };

    const resolveSelectedAnnotation = () => {
        if (localAnnotation && activeAnnotationId === localAnnotation.sample_id) {
            return localAnnotation;
        }

        if (!activeAnnotationId) return localAnnotation;

        return (
            sample.annotations.find((annotation) => annotation.sample_id === activeAnnotationId) ??
            localAnnotation
        );
    };

    const syncLocalMaskFromAnnotation = (annotation: AnnotationView | null) => {
        localAnnotation = annotation;
        const nextMask = annotation?.segmentation_details?.segmentation_mask
            ? decodeRLEToBinaryMask(
                  annotation.segmentation_details.segmentation_mask,
                  sample.width,
                  sample.height
              )
            : new Uint8Array(sample.width * sample.height);
        localMask = nextMask;
        committedMaskDataUrl = '';
        hasLocalChanges = false;
    };

    const getUpsampledMask = (labelId: number) => {
        if (!slicResult) {
            throw new Error('Cannot build label mask without SLIC result');
        }

        const cachedMask = upsampledMaskCache.get(labelId);
        if (cachedMask) {
            return cachedMask;
        }

        const mask = upsampleCellMask(slicResult, labelId);
        upsampledMaskCache.set(labelId, mask);
        return mask;
    };

    const isLabelActiveInMask = (mask: Uint8Array, labelId: number) => {
        const labelMask = getUpsampledMask(labelId);

        for (let index = 0; index < labelMask.length; index++) {
            if (labelMask[index] === 1 && mask[index] === 1) {
                return true;
            }
        }

        return false;
    };

    const applyLabelToMask = (mask: Uint8Array, labelId: number, nextValue: 0 | 1) => {
        const labelMask = getUpsampledMask(labelId);

        for (let index = 0; index < labelMask.length; index++) {
            if (labelMask[index] === 1) {
                mask[index] = nextValue;
            }
        }
    };

    const getHoverMaskDataUrl = (labelId: number) => {
        const cached = hoverMaskCache.get(labelId);
        if (cached) return cached;

        if (!slicResult) {
            throw new Error('Cannot build hover mask without SLIC result');
        }

        const hoverMask = extractCellMask(slicResult.labels, slicResult.width, slicResult.height, labelId);
        const dataUrl = maskToColoredDataUrl(
            hoverMask,
            slicResult.width,
            slicResult.height,
            hoverColor
        );
        hoverMaskCache.set(labelId, dataUrl);
        return dataUrl;
    };

    const loadSlicResult = async () => {
        setSlicStatus('computing');
        hoveredLabel = null;
        hoverMaskDataUrl = '';
        hoverMaskCache = new Map();
        upsampledMaskCache = new Map();
        strokeMaskDataUrl = '';
        committedMaskDataUrl = '';

        try {
            const result = await loadSuperpixelsForImage({
                imageUrl,
                level: sampleDetailsToolbarContext.slic.level
            });

            slicResult = result;
            boundaryDataUrl = maskToColoredDataUrl(
                result.boundaries,
                result.width,
                result.height,
                boundaryColor
            );
            setSlicStatus('ready');
        } catch (error) {
            console.error('Failed to compute SLIC superpixels:', error);
            slicResult = null;
            boundaryDataUrl = '';
            setSlicStatus('error');
        }
    };

    const updateHoveredLabel = (point: { x: number; y: number } | null) => {
        if (!point || !slicResult) return;

        const nextLabel = getLabelAtPoint(slicResult, point.x, point.y);
        if (hoveredLabel === nextLabel) return;

        hoveredLabel = nextLabel;
        hoverMaskDataUrl = getHoverMaskDataUrl(nextLabel);
    };

    const processStrokePoint = (
        point: { x: number; y: number } | null
    ) => {
        const currentMask = localMask;
        if (!point || !slicResult || !currentMask) return;

        const points =
            lastStrokePoint === null ? [point] : interpolateLineBetweenPoints(lastStrokePoint, point);
        let nextTouchedLabels = new Set(strokeTouchedLabels);
        let nextStrokeMode = strokeMode;
        let didChangeStroke = false;

        for (const strokePoint of points) {
            const labelId = getLabelAtPoint(slicResult, strokePoint.x, strokePoint.y);

            if (nextStrokeMode === null) {
                nextStrokeMode = isLabelActiveInMask(currentMask, labelId) ? 'erase' : 'add';
            }

            if (nextTouchedLabels.has(labelId) || !nextStrokeMode) {
                continue;
            }

            nextTouchedLabels.add(labelId);
            didChangeStroke = true;
        }

        strokeMode = nextStrokeMode;
        if (didChangeStroke) {
            strokeTouchedLabels = nextTouchedLabels;
            strokeMaskDataUrl = maskToColoredDataUrl(
                createSlicMaskForLabels(slicResult, nextTouchedLabels),
                slicResult.width,
                slicResult.height,
                hoverColor
            );
        }

        lastStrokePoint = point;
        updateHoveredLabel(point);
    };

    const persistStroke = async () => {
        if (!localMask || isPersisting || !hasLocalChanges) {
            return;
        }

        isPersisting = true;

        try {
            const persistedAnnotation = await brushApi.finishBrush(
                new Uint8Array(localMask),
                resolveSelectedAnnotation(),
                $labels.data ?? [],
                updateAnnotation,
                annotationLabelContext.lockedAnnotationIds,
                {
                    deferDrawingReset: true,
                    skipImageRefetch: true,
                    refreshAnnotations
                }
            );

            if (persistedAnnotation) {
                localAnnotation = persistedAnnotation;
                setAnnotationId(persistedAnnotation.sample_id);
                hasLocalChanges = false;
                pendingServerSync = true;
                pendingServerSyncAnnotationId = persistedAnnotation.sample_id;
                pendingServerSyncMask =
                    persistedAnnotation.segmentation_details?.segmentation_mask ?? null;
                committedMaskDataUrl = strokeMaskDataUrl;
                strokeMaskDataUrl = '';
                setIsDrawing(true);
            }
        } finally {
            isPersisting = false;
        }
    };

    $effect(() => {
        const nextLoadKey =
            sampleDetailsToolbarContext.status === 'slic'
                ? `${imageUrl}::${sampleDetailsToolbarContext.slic.level}`
                : null;

        if (nextLoadKey === null) {
            slicLoadKey = null;
            hoveredLabel = null;
            hoverMaskDataUrl = '';
            strokeMaskDataUrl = '';
            committedMaskDataUrl = '';
            pendingServerSync = false;
            pendingServerSyncAnnotationId = null;
            pendingServerSyncMask = null;
            return;
        }

        if (slicLoadKey === nextLoadKey) {
            return;
        }

        slicLoadKey = nextLoadKey;
        void loadSlicResult();
    });

    $effect(() => {
        if (isPersisting || isStrokeActive || hasLocalChanges || pendingServerSync) {
            return;
        }

        const selectedAnnotation = activeAnnotationId
            ? (sample.annotations.find((annotation) => annotation.sample_id === activeAnnotationId) ?? null)
            : null;
        if (
            selectedAnnotation?.sample_id === localAnnotation?.sample_id &&
            areMasksEqual(
                selectedAnnotation?.segmentation_details?.segmentation_mask,
                localAnnotation?.segmentation_details?.segmentation_mask
            )
        ) {
            return;
        }

        syncLocalMaskFromAnnotation(selectedAnnotation);
    });

    $effect(() => {
        if (!pendingServerSync || !pendingServerSyncAnnotationId || !pendingServerSyncMask) {
            return;
        }

        const syncedAnnotation = sample.annotations.find(
            (annotation) =>
                annotation.sample_id === pendingServerSyncAnnotationId &&
                areMasksEqual(
                    annotation.segmentation_details?.segmentation_mask,
                    pendingServerSyncMask
                )
        );

        if (!syncedAnnotation) {
            return;
        }

        pendingServerSync = false;
        pendingServerSyncAnnotationId = null;
        pendingServerSyncMask = null;
        committedMaskDataUrl = '';
        setIsDrawing(false);
        syncLocalMaskFromAnnotation(syncedAnnotation);
    });
</script>

{#if slicResult && boundaryDataUrl}
    <image href={boundaryDataUrl} width={sample.width} height={sample.height} opacity={0.9} />
{/if}
{#if slicResult && committedMaskDataUrl}
    <image href={committedMaskDataUrl} width={sample.width} height={sample.height} opacity={1} />
{/if}
{#if slicResult && strokeMaskDataUrl}
    <image href={strokeMaskDataUrl} width={sample.width} height={sample.height} opacity={1} />
{/if}
{#if slicResult && hoverMaskDataUrl}
    <image href={hoverMaskDataUrl} width={sample.width} height={sample.height} opacity={1} />
{/if}
<SampleAnnotationRect
    bind:interactionRect
    {sample}
    cursor={'crosshair'}
    onpointermove={(event) => {
        const point = getImageCoordsFromMouse(event, interactionRect, sample.width, sample.height);

        if (isStrokeActive) {
            processStrokePoint(point);
            return;
        }

        updateHoveredLabel(point);
    }}
    onpointerleave={() => {
        if (isStrokeActive) return;
        hoveredLabel = null;
        hoverMaskDataUrl = '';
    }}
    onpointerdown={(event) => {
        const targetAnnotation = resolveSelectedAnnotation();
        if (
            !slicResult ||
            isPersisting ||
            targetAnnotation &&
            annotationLabelContext.isAnnotationLocked?.(targetAnnotation.sample_id)
        ) {
            event.currentTarget?.releasePointerCapture?.(event.pointerId);
            return;
        }

        event.currentTarget?.setPointerCapture?.(event.pointerId);
        setIsDrawing(true);
        isStrokeActive = true;
        strokeTouchedLabels = new Set();
        strokeMode = null;
        lastStrokePoint = null;
        strokeMaskDataUrl = '';

        if (!annotationLabelContext.annotationId && activeAnnotationId) {
            setAnnotationId(activeAnnotationId);
        } else if (!annotationLabelContext.annotationId && localAnnotation?.sample_id) {
            setAnnotationId(localAnnotation.sample_id);
        }

        const startingMask = localMask ?? new Uint8Array(sample.width * sample.height);

        if (!localMask) {
            localMask = startingMask;
        }

        const point = getImageCoordsFromMouse(event, interactionRect, sample.width, sample.height);
        processStrokePoint(point);
    }}
    onpointerup={(event) => {
        event.currentTarget?.releasePointerCapture?.(event.pointerId);

        if (!isStrokeActive) {
            return;
        }

        isStrokeActive = false;
        lastStrokePoint = null;
        const touchedLabels = new Set(strokeTouchedLabels);
        const completedStrokeMode = strokeMode;
        strokeTouchedLabels = new Set();
        strokeMode = null;

        if (!slicResult || !localMask || touchedLabels.size === 0 || !completedStrokeMode) {
            strokeMaskDataUrl = '';
            setIsDrawing(false);
            return;
        }

        const nextMask = new Uint8Array(localMask);
        const nextValue = completedStrokeMode === 'add' ? 1 : 0;

        for (const labelId of touchedLabels) {
            applyLabelToMask(nextMask, labelId, nextValue);
        }

        localMask = nextMask;
        hasLocalChanges = true;

        void persistStroke();
    }}
/>
