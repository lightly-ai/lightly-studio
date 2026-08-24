<script lang="ts">
    import { SampleImage, SelectableBox } from '$lib/components';
    import { useClassifierState } from '$lib/hooks/useClassifiers/useClassifierState';
    import { useImagesInfinite } from '$lib/hooks/useImagesInfinite/useImagesInfinite';
    import { useSettings } from '$lib/hooks/useSettings';
    import {
        CLASSIFIER_CREATION_CANDIDATE_LIMIT,
        mergeClassifierCandidates
    } from '$lib/hooks/useClassifiers/classifierCandidates';
    import { Grid } from 'svelte-virtual';
    import type { ImageView } from '$lib/api/lightly_studio_local';
    import { get } from 'svelte/store';
    import { untrack } from 'svelte';

    interface Props {
        collection_id: string;
        source?: 'collection' | 'classifier';
        sampleLimit?: number;
        onDisplayedSampleCountChange?: (count: number) => void;
    }

    const {
        collection_id,
        source = 'classifier',
        sampleLimit,
        onDisplayedSampleCountChange
    }: Props = $props();

    const { classifierSamples, classifierSelectedSampleIds, toggleClassifierSampleSelection } =
        useClassifierState();
    const { gridViewSampleRenderingStore } = useSettings();
    const initialSelectedSampleIds = untrack(() =>
        source === 'collection'
            ? Array.from(get(classifierSelectedSampleIds)).slice(
                  0,
                  sampleLimit ?? CLASSIFIER_CREATION_CANDIDATE_LIMIT
              )
            : []
    );

    const { samples: infiniteSamples } = useImagesInfinite(() =>
        source === 'collection'
            ? { collection_id, mode: 'normal' as const, filters: {} }
            : {
                  collection_id,
                  mode: 'classifier' as const,
                  classifierSamples: $classifierSamples || undefined
              }
    );
    const { samples: initialSelectedSamples } = useImagesInfinite(() => ({
        collection_id,
        mode: 'normal' as const,
        filters: { sample_ids: initialSelectedSampleIds },
        enabled: source === 'collection' && initialSelectedSampleIds.length > 0
    }));

    const collectionSamples = $derived(
        infiniteSamples.data?.pages.flatMap((page) => page.data) ?? []
    );
    const preferredSamples = $derived(
        initialSelectedSamples.data?.pages.flatMap((page) => page.data) ?? []
    );
    const orderedPreferredSamples = $derived(
        initialSelectedSampleIds.flatMap((sampleId) =>
            preferredSamples.filter((sample) => sample.sample_id === sampleId)
        )
    );

    const displayedSamples: ImageView[] = $derived(
        source === 'collection'
            ? mergeClassifierCandidates(
                  orderedPreferredSamples,
                  collectionSamples,
                  sampleLimit ?? CLASSIFIER_CREATION_CANDIDATE_LIMIT
              )
            : infiniteSamples.data &&
                $classifierSamples &&
                ($classifierSamples.positiveSampleIds.length > 0 ||
                    $classifierSamples.negativeSampleIds.length > 0)
              ? collectionSamples
              : []
    );
    const isPending = $derived(
        infiniteSamples.isPending ||
            (initialSelectedSampleIds.length > 0 && initialSelectedSamples.isPending)
    );
    const isError = $derived(
        infiniteSamples.isError ||
            (initialSelectedSampleIds.length > 0 && initialSelectedSamples.isError)
    );

    let viewport: HTMLElement | null = $state(null);
    let objectFit = $state($gridViewSampleRenderingStore);
    // Set initial height
    let viewportHeight = $state(400);

    // Grid configuration - 4 images per row
    const sampleWidth = 160;
    const sampleHeight = 160;
    const GridGap = 6;

    // Update viewport height when viewport changes
    $effect(() => {
        if (viewport) {
            const resizeObserver = new ResizeObserver((entries) => {
                for (const entry of entries) {
                    viewportHeight = Math.max(entry.contentRect.height, 200);
                }
            });
            resizeObserver.observe(viewport);
            return () => resizeObserver.disconnect();
        }
    });

    const handleOnClick: (event: MouseEvent & { currentTarget: HTMLElement }) => void = (event) => {
        const sampleId = event.currentTarget.dataset.sampleId!;
        toggleSampleSelection(sampleId);
    };

    const handleOnDoubleClick: (event: MouseEvent & { currentTarget: HTMLElement }) => void = (
        event
    ) => {
        event.preventDefault();
        const sampleId = event.currentTarget.dataset.sampleId!;
        toggleSampleSelection(sampleId);
    };

    const handleKeyDown: (event: KeyboardEvent & { currentTarget: HTMLElement }) => void = (
        event
    ) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            const sampleId = event.currentTarget.dataset.sampleId!;
            toggleSampleSelection(sampleId);
        }
    };

    function toggleSampleSelection(sampleId: string) {
        toggleClassifierSampleSelection(sampleId);
    }

    function handleScroll(event: Event) {
        if (source === 'collection' || sampleLimit !== undefined) return;

        const viewport = event.currentTarget as HTMLElement;
        // Fetch before the last two rows so users can browse the collection without hitting an
        // empty pause at the end of the currently loaded page.
        const fetchThreshold = sampleHeight * 2;
        const distanceFromBottom =
            viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight;
        if (
            distanceFromBottom < fetchThreshold &&
            infiniteSamples.hasNextPage &&
            !infiniteSamples.isFetchingNextPage
        ) {
            infiniteSamples.fetchNextPage();
        }
    }

    $effect(() => {
        if (!isPending) onDisplayedSampleCountChange?.(displayedSamples.length);
    });
</script>

{#if isPending}
    <!-- Loading state -->
    <div class="flex h-full w-full items-center justify-center">
        <div class="text-sm text-muted-foreground">Loading samples...</div>
    </div>
{:else if isError}
    <!-- Error state -->
    <div class="flex h-full w-full items-center justify-center">
        <div class="text-sm text-muted-foreground">Error loading samples</div>
    </div>
{:else if infiniteSamples.isSuccess && displayedSamples.length === 0}
    <!-- Empty state -->
    <div class="flex h-full w-full items-center justify-center">
        <div class="text-center text-muted-foreground">
            <div class="mb-2 text-sm font-medium">No samples available</div>
            <div class="text-xs">
                {source === 'collection'
                    ? 'This collection does not contain any images.'
                    : 'No samples found for this classifier.'}
            </div>
        </div>
    </div>
{:else}
    <!-- Main grid content -->
    <div class="viewport h-full w-full" bind:this={viewport}>
        {#if displayedSamples.length > 0}
            <Grid
                itemCount={displayedSamples.length}
                itemHeight={sampleHeight + GridGap}
                itemWidth={sampleWidth + GridGap}
                height={viewportHeight}
                onscroll={handleScroll}
                class="overflow-none overflow-y-auto dark:[color-scheme:dark]"
                style="--sample-width: {sampleWidth}px; --sample-height: {sampleHeight}px;"
                overScan={5}
            >
                {#snippet item({ index, style }: { index: number; style: string })}
                    {#if displayedSamples[index]}
                        {#key displayedSamples[index].sample_id}
                            <div {style}>
                                <div
                                    class="relative cursor-pointer overflow-hidden rounded-lg"
                                    class:grid-item-selected={$classifierSelectedSampleIds.has(
                                        displayedSamples[index].sample_id
                                    )}
                                    style="width: {sampleWidth}px; height: {sampleHeight}px;"
                                    data-testid="classifier-sample-grid-item"
                                    data-sample-id={displayedSamples[index].sample_id}
                                    data-sample-name={displayedSamples[index].file_name}
                                    data-index={index}
                                    onclick={handleOnClick}
                                    ondblclick={handleOnDoubleClick}
                                    onkeydown={handleKeyDown}
                                    aria-label={`Select sample: ${displayedSamples[index].file_name}`}
                                    role="button"
                                    tabindex="0"
                                >
                                    {#if $classifierSelectedSampleIds.has(displayedSamples[index].sample_id)}
                                        <div
                                            class="pointer-events-none absolute right-2 top-1.5 z-10"
                                            inert
                                        >
                                            <SelectableBox
                                                onSelect={() => undefined}
                                                isSelected={true}
                                            />
                                        </div>
                                    {/if}

                                    <SampleImage sample={displayedSamples[index]} {objectFit} />
                                </div>
                            </div>
                        {/key}
                    {/if}
                {/snippet}
            </Grid>
        {:else}
            <div class="flex h-full w-full items-center justify-center">
                <div class="text-sm text-muted-foreground">No samples to display</div>
            </div>
        {/if}
    </div>
{/if}

<style>
    .viewport {
        overflow-y: hidden;
    }
</style>
