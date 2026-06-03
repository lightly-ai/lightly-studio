<script lang="ts">
    import type { ImageView } from '$lib/api/lightly_studio_local';
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
    import { getColorByLabel } from '$lib/utils';
    import { getColorPair } from '$lib/utils/getColorPair';
    import {
        getSampleClassificationPills,
        type SampleClassificationPill
    } from './getSampleClassificationPills';

    let {
        sample,
        hasBottomOverlay = false,
        hasRightOverlay = false
    }: {
        sample: Pick<ImageView, 'annotations'>;
        hasBottomOverlay?: boolean;
        hasRightOverlay?: boolean;
    } = $props();

    let containerWidth = $state(0);
    let pillsWidth = $state(0);

    const { selectedCollectionIds, collectionIdToName } = useAnnotationCollectionsFilter();
    const { customLabelColorsStore } = useCustomLabelColors();

    const pills = $derived(
        getSampleClassificationPills({
            annotations: sample.annotations,
            selectedCollectionIds: $selectedCollectionIds,
            collectionIdToName: $collectionIdToName
        })
    );

    const overflowCount = $derived(pillsWidth > containerWidth ? Math.max(0, pills.length - 1) : 0);
    const visiblePills = $derived(overflowCount > 0 ? pills.slice(0, 1) : pills);

    const getPillColor = (pill: SampleClassificationPill, alpha: number) => {
        const customColor = $customLabelColorsStore[pill.label];
        if (!customColor) {
            return getColorByLabel(pill.colorKey, alpha);
        }

        const hex = customColor.color.slice(1);
        const r = parseInt(hex.slice(0, 2), 16);
        const g = parseInt(hex.slice(2, 4), 16);
        const b = parseInt(hex.slice(4, 6), 16);

        return getColorPair({ r, g, b }, customColor.alpha * alpha);
    };
</script>

{#if pills.length > 0}
    <div
        bind:clientWidth={containerWidth}
        class="pointer-events-none absolute left-1 z-10 overflow-hidden {hasBottomOverlay
            ? 'bottom-8'
            : 'bottom-1'} {hasRightOverlay ? 'right-14' : 'right-1'}"
    >
        <div class="flex flex-nowrap items-center gap-1 overflow-hidden">
            {#each visiblePills as pill (pill.id)}
                {@const pillColor = getPillColor(pill, 0.9)}
                {@const pillBorderColor = getPillColor(pill, 1)}
                <span
                    class="inline-flex h-5 min-w-0 max-w-32 box-border items-center truncate rounded border px-1.5 text-xs font-medium backdrop-blur-sm"
                    style={`background-color: ${pillColor.color}; border-color: ${pillBorderColor.color}; color: ${pillColor.contrastColor};`}
                    title={pill.title}
                >
                    {pill.displayLabel}
                </span>
            {/each}
            {#if overflowCount > 0}
                <span
                    class="inline-flex h-5 shrink-0 box-border items-center rounded bg-black/60 px-1.5 text-xs font-medium text-white backdrop-blur-sm"
                    title={`${overflowCount} more classification labels`}
                >
                    +{overflowCount}
                </span>
            {/if}
        </div>
    </div>
    <div class="pointer-events-none absolute left-1 top-0 -z-10 opacity-0" aria-hidden="true">
        <div bind:clientWidth={pillsWidth} class="inline-flex flex-nowrap items-center gap-1">
            {#each pills as pill (pill.id)}
                {@const pillColor = getPillColor(pill, 0.9)}
                {@const pillBorderColor = getPillColor(pill, 1)}
                <span
                    class="inline-flex h-5 max-w-32 box-border items-center truncate rounded border px-1.5 text-xs font-medium backdrop-blur-sm"
                    style={`background-color: ${pillColor.color}; border-color: ${pillBorderColor.color}; color: ${pillColor.contrastColor};`}
                >
                    {pill.displayLabel}
                </span>
            {/each}
        </div>
    </div>
{/if}
