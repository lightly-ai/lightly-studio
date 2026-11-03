<script lang="ts">
    import { Layers, Tag } from '@lucide/svelte';
    import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import { useSettings } from '$lib/hooks/useSettings';
    import type { getTileFieldKind } from '$lib/hooks/useTileFields/useTileFields';
    import { getColorByLabel, resolveEffectiveColorBySource } from '$lib/utils';

    interface Props {
        kind: ReturnType<typeof getTileFieldKind>;
        /** The annotation class or source name that picks the color. Generic fields have none. */
        name?: string;
    }

    const { kind, name }: Props = $props();

    const { customLabelColorsStore } = useCustomLabelColors();
    const { multipleSourcesVisible } = useAnnotationCollectionsFilter();
    const { enforceColoringByClassStore } = useSettings();

    // The store holds custom colors and is refreshed when the class color order changes, so
    // reading it keeps the color in step with boxes and plots.
    const color = $derived(
        name && $customLabelColorsStore ? getColorByLabel(name).color : undefined
    );
    // Sources have a color only while boxes are colored by source, as in the side menu.
    const showSourceColor = $derived(
        resolveEffectiveColorBySource({
            multipleSourcesVisible: $multipleSourcesVisible,
            enforceColoringByClass: $enforceColoringByClassStore
        })
    );
</script>

{#if kind === 'class'}
    <!-- The generic class field has no single class, so its dot shows a mix of colors. -->
    <span
        class="inline-block size-2 shrink-0 rounded-full ring-1 ring-white/50 {color
            ? ''
            : 'bg-gradient-to-br from-rose-500 via-amber-400 to-sky-500'}"
        style:background-color={color}
        aria-hidden="true"
    ></span>
{:else if kind === 'source'}
    <Layers class="size-3 shrink-0" aria-hidden="true" />
    {#if color && showSourceColor}
        <span
            class="inline-block size-2 shrink-0 rounded-sm ring-1 ring-white/50"
            style:background-color={color}
            aria-hidden="true"
        ></span>
    {/if}
{:else if kind === 'tag'}
    <Tag class="size-3 shrink-0" aria-hidden="true" />
{/if}
