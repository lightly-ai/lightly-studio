<script lang="ts">
    import { ChevronDown } from '@lucide/svelte';
    import * as Popover from '$lib/components/ui/popover';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useRecentClasses, useSettings, useStickyClass } from '$lib/hooks';
    import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { resolveTargetSource } from '$lib/hooks/useAnnotationTarget/resolveTargetSource';
    import { useSetTargetSource } from '$lib/hooks/useAnnotationTarget/useSetTargetSource';
    import { usePendingBoxClass } from '$lib/hooks/usePendingBoxClass/usePendingBoxClass';
    import { getLabelColor } from '$lib/utils';
    import { getShortcutKeys, isSearchStartKey } from '../AnnotationCard/annotationCard.helpers';
    import ClassSearchList from '../ClassSearchList/ClassSearchList.svelte';
    import SourceSearchList from '../SourceSearchList/SourceSearchList.svelte';

    const { collectionId }: { collectionId: string } = $props();
    const { context: annotationLabelContext } = useAnnotationLabelContext();
    const { stickyClasses, pickClass } = useStickyClass();
    const { recentClasses } = useRecentClasses();
    const { settingsStore } = useSettings();
    const { customLabelColorsStore } = useCustomLabelColors();
    const { request: pendingBox } = usePendingBoxClass();
    const setTargetSource = useSetTargetSource(() => collectionId);
    const sources = useAnnotationCollections(() => ({ collectionId }));
    const labels = useAnnotationLabels(() => ({ collectionId }));

    // Stable arrays: the lists reset their first-row highlight when these change identity.
    const sourceList = $derived(sources.data ?? []);
    const classNames = $derived((labels.data ?? []).map((l) => l.annotation_label_name));
    const recent = $derived($recentClasses[collectionId] ?? []);
    const source = $derived(
        resolveTargetSource(
            annotationLabelContext.annotationSource,
            sourceList.map((s) => s.name)
        )
    );
    const className = $derived($stickyClasses[collectionId]);
    // The same colors as the card header and the canvas.
    const sourceColor = $derived(
        source ? getLabelColor($customLabelColorsStore, source) : undefined
    );
    const classColor = $derived(
        className ? getLabelColor($customLabelColorsStore, className) : undefined
    );

    let isSourceOpen = $state(false);
    let isClassOpen = $state(false);
    let query = $state('');

    // The card owns the keys while an annotation is selected or a box is pending. The search
    // key check also skips text fields and overlays.
    const handleKeydown = (event: KeyboardEvent) => {
        if (annotationLabelContext.annotationId || $pendingBox) return;
        if (!isSearchStartKey(event, getShortcutKeys($settingsStore))) return;
        event.preventDefault();
        query = event.key;
        isClassOpen = true;
    };
    const partClass = (isSet: boolean) =>
        `inline-flex h-8 items-center gap-1 px-2 text-sm hover:bg-accent ${isSet ? '' : 'text-amber-600'}`;
</script>

<svelte:window onkeydowncapture={handleKeydown} />

<div
    class="pointer-events-auto absolute left-14 top-1 z-20 inline-flex divide-x overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md"
    data-testid="annotation-target-chip"
>
    <Popover.Root bind:open={isSourceOpen}>
        <Popover.Trigger class={partClass(source !== null)} title="Annotation source">
            {#if source}
                <span
                    class="size-2 shrink-0 rounded-full"
                    style:background-color={sourceColor}
                    data-testid="annotation-target-source-dot"
                ></span>{source}
            {:else}
                Pick a source
            {/if}
            <ChevronDown class="size-3" />
        </Popover.Trigger>
        <Popover.Content class="w-64 p-0" align="start">
            <SourceSearchList
                sources={sourceList}
                onPick={(name) => {
                    setTargetSource(name);
                    isSourceOpen = false;
                }}
                onCancel={() => (isSourceOpen = false)}
            />
        </Popover.Content>
    </Popover.Root>
    <Popover.Root bind:open={isClassOpen} onOpenChange={(open) => !open && (query = '')}>
        <Popover.Trigger class={partClass(!!className)} title="Class for new annotations">
            {#if className}
                <span
                    class="size-2 shrink-0 rounded-full"
                    style:background-color={classColor}
                    data-testid="annotation-target-class-dot"
                ></span>{className}
            {:else}
                Pick a class
            {/if}
            <ChevronDown class="size-3" />
        </Popover.Trigger>
        <Popover.Content class="w-64 p-0" align="start">
            <ClassSearchList
                names={classNames}
                {recent}
                initialQuery={query}
                onPick={(name) => {
                    pickClass(collectionId, name);
                    isClassOpen = false;
                }}
                onCancel={() => (isClassOpen = false)}
            />
        </Popover.Content>
    </Popover.Root>
</div>
