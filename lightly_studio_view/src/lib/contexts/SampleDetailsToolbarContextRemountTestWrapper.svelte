<script lang="ts">
    import SampleDetailsToolbarContextRemountChild from './SampleDetailsToolbarContextRemountChild.svelte';
    import {
        createSampleDetailsToolbarContext,
        useSampleDetailsToolbarContext
    } from './SampleDetailsToolbar.svelte';

    createSampleDetailsToolbarContext();
    const { setStatus } = useSampleDetailsToolbarContext();
    let mounted = $state(true);
</script>

<button aria-label="Set brush" onclick={() => setStatus('brush')}>Set brush</button>
<button aria-label="Toggle child" onclick={() => (mounted = !mounted)}>Toggle child</button>
{#if mounted}
    <SampleDetailsToolbarContextRemountChild />
{/if}
