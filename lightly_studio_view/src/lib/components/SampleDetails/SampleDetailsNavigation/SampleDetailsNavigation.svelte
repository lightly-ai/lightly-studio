<script lang="ts">
    import { page } from '$app/state';
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import type { Writable } from 'svelte/store';
    import type { SampleAdjacents as SampleAdjacentsState } from '$lib/hooks/useSampleAdjacents/useSampleAdjacents';
    import SteppingNavigation from '$lib/components/SteppingNavigation/SteppingNavigation.svelte';

    const sampleIndex = $derived(page.data.sampleIndex);
    const sampleAdjacents = $derived(page.data.sampleAdjacents as Writable<SampleAdjacentsState>);

    const gotoNextSample = () => {
        if ($sampleAdjacents.sampleNext) {
            goto(
                routeHelpers.toSample({
                    sampleId: $sampleAdjacents.sampleNext.sample_id,
                    datasetId: $sampleAdjacents.sampleNext.dataset_id,
                    sampleIndex: sampleIndex + 1
                }),
                {
                    invalidateAll: true
                }
            );
        }
    };

    const gotoPreviousSample = () => {
        if ($sampleAdjacents.samplePrevious) {
            goto(
                routeHelpers.toSample({
                    sampleId: $sampleAdjacents.samplePrevious.sample_id,
                    datasetId: $sampleAdjacents.samplePrevious.dataset_id,
                    sampleIndex: sampleIndex - 1
                }),
                {
                    invalidateAll: true
                }
            );
        }
    };

    const handleKeyDownEvent = (event: KeyboardEvent) => {
        switch (event.key) {
            case 'ArrowRight':
                gotoNextSample();
                break;
            case 'ArrowLeft':
                gotoPreviousSample();
                break;
        }
    };
</script>

{#if $sampleAdjacents}
    <SteppingNavigation
        hasPrevious={!!$sampleAdjacents.samplePrevious}
        hasNext={!!$sampleAdjacents.sampleNext}
        onPrevious={gotoPreviousSample}
        onNext={gotoNextSample}
    />
{/if}

<svelte:window onkeydown={handleKeyDownEvent} />
