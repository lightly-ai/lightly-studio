<script lang="ts">
    import { SampleImage, SelectableBox } from '$lib/components';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useSamplesInfinite } from '$lib/hooks/useSamplesInfinite/useSamplesInfinite';
    import { useSettings } from '$lib/hooks/useSettings';
    import { Grid } from 'svelte-virtual';
    import type { SampleView } from '$lib/api/lightly_studio_local';
    import { onMount } from 'svelte';

    const { dataset_id }: { dataset_id: string } = $props();

    const { classifierSamples, classifierSelectedSampleIds, toggleClassifierSampleSelection } =
        useGlobalStorage();
    const { gridViewSampleRenderingStore } = useSettings();

    const samplesParams = $derived({
        dataset_id,
        mode: 'classifier' as const,
        classifierSamples: $classifierSamples || undefined
    });

    const { samples: infiniteSamples } = $derived(useSamplesInfinite(samplesParams));

    const displayedSamples: SampleView[] = $derived(
        $infiniteSamples && $infiniteSamples.data
            ? $infiniteSamples.data.pages.flatMap((page) => page.data)
            : []
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

    function handleOnClick(event: Event) {
        const sampleId = (event.currentTarget as HTMLElement).dataset.sampleId!;
        toggleSampleSelection(sampleId);
    }

    function handleOnDoubleClick(event: Event) {
        event.preventDefault();
        const sampleId = (event.currentTarget as HTMLElement).dataset.sampleId!;
        toggleSampleSelection(sampleId);
    }

    function handleKeyDown(event: KeyboardEvent) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            const sampleId = (event.currentTarget as HTMLElement).dataset.sampleId!;
            toggleSampleSelection(sampleId);
        }
    }

    function toggleSampleSelection(sampleId: string) {
        toggleClassifierSampleSelection(sampleId);
    }
</script>

{#if $infiniteSamples.isPending}
    <!-- Loading state -->
    <div class="flex h-full w-full items-center justify-center">
        <div class="text-sm text-muted-foreground">Loading samples...</div>
    </div>
{:else if $infiniteSamples.isError}
    <!-- Error state -->
    <div class="flex h-full w-full items-center justify-center">
        <div class="text-sm text-muted-foreground">Error loading samples</div>
    </div>
{:else if $infiniteSamples.isSuccess && displayedSamples.length === 0}
    <!-- Empty state -->
    <div class="flex h-full w-full items-center justify-center">
        <div class="text-center text-muted-foreground">
            <div class="mb-2 text-sm font-medium">No samples available</div>
            <div class="text-xs">No samples found for this classifier.</div>
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
                class="overflow-none overflow-y-auto dark:[color-scheme:dark]"
                style="--sample-width: {sampleWidth}px; --sample-height: {sampleHeight}px;"
                overScan={5}
            >
                {#snippet item({ index, style }: { index: number; style: string })}
                    {#key $infiniteSamples.dataUpdatedAt}
                        {#if displayedSamples[index]}
                            <div
                                class="relative cursor-pointer"
                                class:sample-selected={$classifierSelectedSampleIds.has(
                                    displayedSamples[index].sample_id
                                )}
                                {style}
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
                                <div class="absolute inset-0 z-10">
                                    <SelectableBox
                                        onSelect={() => undefined}
                                        isSelected={$classifierSelectedSampleIds.has(
                                            displayedSamples[index].sample_id
                                        )}
                                    />
                                </div>

                                <SampleImage sample={displayedSamples[index]} {objectFit} />
                            </div>
                        {/if}
                    {/key}
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

    .sample-selected {
        outline: drop-shadow(1px 1px 1px hsl(var(--primary)))
            drop-shadow(1px -1px 1px hsl(var(--primary)))
            drop-shadow(-1px -1px 1px hsl(var(--primary)))
            drop-shadow(-1px 1px 1px hsl(var(--primary)));
    }
</style>
