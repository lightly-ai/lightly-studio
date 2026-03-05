<script lang="ts">
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import { onDestroy, onMount, type ComponentProps } from 'svelte';
    import SampleAnnotation from '../SampleAnnotation/SampleAnnotation.svelte';
    import type { SampleImageObjectFit } from '../SampleImage/types';
    import type { ImageView } from '$lib/api/lightly_studio_local';

    const {
        sample,
        containerWidth,
        containerHeight,
        sampleImageObjectFit = 'contain',
        showLabel
    }: {
        sample: ImageView;
        containerWidth: number;
        containerHeight: number;
        sampleImageObjectFit?: SampleImageObjectFit;
        showLabel?: ComponentProps<typeof SampleAnnotation>['showLabel'];
    } = $props();

    const { isHidden } = useHideAnnotations();
    const annotationsWithVisuals = $derived(
        sample.annotations.filter((annotation) => annotation.annotation_type !== 'classification')
    );

    let showAnnotations = $state(false);

    const SHOW_ANNOTATIONS_AFTER_RESIZE_MS = 120;
    const idle = window.requestIdleCallback?.bind(window);
    const cancelIdle = window.cancelIdleCallback?.bind(window);
    let idleHandle: number | null = null;
    let timeoutHandle: ReturnType<typeof setTimeout> | null = null;
    let previousContainerWidth = $state<number | null>(null);
    let previousContainerHeight = $state<number | null>(null);

    const clearScheduledShowAnnotations = () => {
        if (idleHandle !== null && cancelIdle) {
            cancelIdle(idleHandle);
            idleHandle = null;
        }

        if (timeoutHandle !== null) {
            clearTimeout(timeoutHandle);
            timeoutHandle = null;
        }
    };

    const scheduleShowAnnotations = (delayMs = 0) => {
        clearScheduledShowAnnotations();

        const revealAnnotations = () => {
            idleHandle = null;
            showAnnotations = true;
        };

        const enqueueReveal = () => {
            if (idle) {
                idleHandle = idle(revealAnnotations, { timeout: SHOW_ANNOTATIONS_AFTER_RESIZE_MS });
                return;
            }

            timeoutHandle = setTimeout(() => {
                timeoutHandle = null;
                revealAnnotations();
            }, 10);
        };

        if (delayMs <= 0) {
            enqueueReveal();
            return;
        }

        timeoutHandle = setTimeout(() => {
            timeoutHandle = null;
            enqueueReveal();
        }, delayMs);
    };

    onMount(() => {
        scheduleShowAnnotations();
    });

    onDestroy(() => {
        clearScheduledShowAnnotations();
    });

    $effect(() => {
        const widthChanged =
            previousContainerWidth !== null && previousContainerWidth !== containerWidth;
        const heightChanged =
            previousContainerHeight !== null && previousContainerHeight !== containerHeight;

        previousContainerWidth = containerWidth;
        previousContainerHeight = containerHeight;

        if (!widthChanged && !heightChanged) {
            return;
        }

        showAnnotations = false;
        scheduleShowAnnotations(SHOW_ANNOTATIONS_AFTER_RESIZE_MS);
    });
</script>

{#if showAnnotations}
    <svg
        style="position: absolute; top: 0; left: 0;"
        class="pointer-events-none"
        viewBox={`0 0 ${sample.width} ${sample.height}`}
        preserveAspectRatio={sampleImageObjectFit === 'contain'
            ? 'xMidYMid meet'
            : 'xMidYMid slice'}
        width={containerWidth}
        height={containerHeight}
    >
        <g class:invisible={$isHidden}>
            {#each annotationsWithVisuals as annotation (annotation.sample_id)}
                <SampleAnnotation {annotation} {showLabel} imageWidth={sample.width} />
            {/each}
        </g>
    </svg>
{/if}
