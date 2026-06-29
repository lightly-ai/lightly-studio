<script lang="ts">
    import {
        EvaluationMatchType,
        type AnnotationView,
        type EvaluationMatchView,
        type ImageAnnotationView
    } from '$lib/api/lightly_studio_local';
    import { getBoundingBox } from '$lib/components/SampleAnnotation/utils';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useSettings } from '$lib/hooks/useSettings';
    import { getGridImageURL, getGridThumbnailRequestSize } from '$lib/utils';

    type Props = {
        match: EvaluationMatchView;
        containerWidth: number;
        containerHeight: number;
        cachedCollectionVersion: string;
    };

    let { match, containerWidth, containerHeight, cachedCollectionVersion = '' }: Props = $props();

    const padding = 20;

    // Role-based colors so localization vs class errors are easy to read:
    // ground truth in green, prediction in blue.
    const GT_COLOR = '#22c55e';
    const PRED_COLOR = '#3b82f6';

    const BADGE: Record<EvaluationMatchType, { label: string; color: string }> = {
        [EvaluationMatchType.TP]: { label: 'TP', color: '#16a34a' },
        [EvaluationMatchType.FP]: { label: 'FP', color: '#dc2626' },
        [EvaluationMatchType.FN]: { label: 'FN', color: '#d97706' }
    };

    const { getCollectionVersion } = useGlobalStorage();
    const { gridViewThumbnailQualityStore } = useSettings();

    const image: ImageAnnotationView = $derived(match.parent_sample_data);

    let collectionVersion = $state(cachedCollectionVersion);
    let collectionVersionLoaded = $state(!!cachedCollectionVersion);

    $effect(() => {
        if (!cachedCollectionVersion && image?.sample?.collection_id && !collectionVersionLoaded) {
            (async () => {
                collectionVersion = await getCollectionVersion(image.sample.collection_id);
                collectionVersionLoaded = true;
            })();
        }
        if (cachedCollectionVersion && !collectionVersionLoaded) {
            collectionVersionLoaded = true;
        }
    });

    const imageUrl = $derived(
        image
            ? getGridImageURL({
                  sampleId: image.sample_id,
                  quality: $gridViewThumbnailQualityStore,
                  renderedWidth: getGridThumbnailRequestSize(
                      containerWidth,
                      globalThis.window?.devicePixelRatio || 1
                  ),
                  renderedHeight: getGridThumbnailRequestSize(
                      containerHeight,
                      globalThis.window?.devicePixelRatio || 1
                  ),
                  cacheBuster: collectionVersion
              })
            : ''
    );

    type Box = {
        x: number;
        y: number;
        width: number;
        height: number;
        color: string;
        label: string;
        role: 'GT' | 'Pred';
    };

    const buildBox = (
        annotation: AnnotationView | null | undefined,
        color: string,
        role: 'GT' | 'Pred'
    ): Box | null => {
        if (!annotation?.object_detection_details) {
            return null;
        }
        const bbox = getBoundingBox(annotation);
        return {
            ...bbox,
            color,
            role,
            label: annotation.annotation_label.annotation_label_name
        };
    };

    const boxes: Box[] = $derived(
        [
            buildBox(match.gt_annotation, GT_COLOR, 'GT'),
            buildBox(match.pred_annotation, PRED_COLOR, 'Pred')
        ].filter((box): box is Box => box !== null)
    );

    // Crop region = union of the boxes present, so a TP shows both boxes together.
    const union = $derived.by(() => {
        if (boxes.length === 0) {
            return { x: 0, y: 0, width: image?.width ?? 1, height: image?.height ?? 1 };
        }
        const minX = Math.min(...boxes.map((box) => box.x));
        const minY = Math.min(...boxes.map((box) => box.y));
        const maxX = Math.max(...boxes.map((box) => box.x + box.width));
        const maxY = Math.max(...boxes.map((box) => box.y + box.height));
        return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
    });

    const scale = $derived(
        Math.min(
            containerWidth / (union.width + padding * 2),
            containerHeight / (union.height + padding * 2)
        )
    );

    const xOffset = $derived(
        -(union.x - padding) * scale + (containerWidth - (union.width + padding * 2) * scale) / 2
    );
    const yOffset = $derived(
        -(union.y - padding) * scale + (containerHeight - (union.height + padding * 2) * scale) / 2
    );

    const badge = $derived(BADGE[match.match_type]);
</script>

<div
    class="crop rounded-lg bg-black"
    style={`
        width: ${containerWidth}px;
        height: ${containerHeight}px;
        background-image: url("${imageUrl}");
        background-position: ${xOffset}px ${yOffset}px;
        background-size: ${(image?.width ?? 0) * scale}px ${(image?.height ?? 0) * scale}px;
        background-repeat: no-repeat;
    `}
>
    {#each boxes as box (box.role)}
        <div
            class="annotation-box"
            style={`
                left: ${xOffset + box.x * scale}px;
                top: ${yOffset + box.y * scale}px;
                width: ${box.width * scale}px;
                height: ${box.height * scale}px;
                border-color: ${box.color};
            `}
        >
            <div
                class="annotation-label flex items-center gap-1 text-xs text-white"
                class:annotation-label--bottom={box.role === 'Pred'}
                style={`background-color: ${box.color};`}
            >
                <span class="font-mono opacity-90">{box.role}</span>
                <span class="truncate">{box.label}</span>
            </div>
        </div>
    {/each}

    <div
        class="badge flex items-center gap-1 text-xs font-semibold text-white"
        style={`background-color: ${badge.color};`}
        data-testid="evaluation-match-badge"
    >
        <span>{badge.label}</span>
        {#if match.iou != null}
            <span class="font-mono opacity-90">{match.iou.toFixed(2)}</span>
        {/if}
    </div>
</div>

<style>
    .crop {
        position: relative;
        overflow: hidden;
    }

    .annotation-box {
        position: absolute;
        border: 2px solid transparent;
        box-sizing: border-box;
    }

    .annotation-label {
        position: absolute;
        top: 0;
        left: 0;
        transform: translate3d(0, -100%, 0);
        padding: 1px 4px;
        white-space: nowrap;
        max-width: 100%;
    }

    /* Anchor the prediction label below its box so it does not overlap the
       ground-truth label (the two boxes sit on top of each other for TPs). */
    .annotation-label--bottom {
        top: auto;
        bottom: 0;
        transform: translate3d(0, 100%, 0);
    }

    .badge {
        position: absolute;
        top: 6px;
        left: 6px;
        padding: 1px 6px;
        border-radius: 4px;
    }
</style>
