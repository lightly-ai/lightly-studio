<script lang="ts">
    import {
        createSampleDetailsToolbarContext,
        useSampleDetailsToolbarContext
    } from './SampleDetailsToolbar.svelte';

    createSampleDetailsToolbarContext();
    const { context } = useSampleDetailsToolbarContext();
</script>

<div data-testid="toolbar-status">{context.status}</div>
