<script lang="ts">
    import { useSlicResult } from './useSlicResult.svelte';
    let {
        imageUrl,
        level = 'medium',
        color = 'blue'
    }: ReturnType<Parameters<typeof useSlicResult>[0]> = $props();
    const slic = useSlicResult(() => ({ imageUrl, level, color }));
</script>

<p role="status">{slic.status}</p>
{#if slic.result}
    <img alt="Superpixel boundaries" src={slic.boundaryDataUrl} />
{/if}
