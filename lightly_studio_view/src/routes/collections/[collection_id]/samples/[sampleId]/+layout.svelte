<script lang="ts">
    import { page } from '$app/state';
    import { SampleDetails } from '$lib/components';

    const { children } = $props();

    const sampleId = $derived(page.params.sampleId);
    const collection = page.data.collection;
    const sampleIndex = $derived(Number(page.params.sampleIndex));
</script>

<div class="flex h-full w-full space-x-4 px-4 pb-4" data-testid="sample-details">
    <div class="h-full w-full space-y-6 rounded-[1vw] bg-card p-4">
        <SampleDetails {sampleId} {collection} {sampleIndex}>
            {#if children}
                {@render children()}
            {/if}
        </SampleDetails>
    </div>
</div>
