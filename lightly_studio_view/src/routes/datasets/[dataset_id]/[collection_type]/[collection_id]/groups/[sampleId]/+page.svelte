<script lang="ts">
    import { createSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';

    createSampleDetailsToolbarContext();
</script>

<div class="flex h-full w-full space-x-4 px-4 pb-4" data-testid="sample-details">
    <div class="h-full w-full space-y-6 rounded-[1vw] bg-card p-4">Group details</div>
</div>
