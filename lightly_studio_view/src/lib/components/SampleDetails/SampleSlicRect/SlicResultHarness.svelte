<script lang="ts">
    import { useSlicResult } from './useSlicResult.svelte';
    interface Props {
        imageUrl: string;
        level?: ReturnType<Parameters<typeof useSlicResult>[0]>['level'];
        color?: string;
    }
    let { imageUrl, level = 'medium', color = 'blue' }: Props = $props();
    const slic = useSlicResult(() => ({ imageUrl, level, color }));
</script>

<p role="status">{slic.status}</p>
{#if slic.result}
    <img alt="Superpixel boundaries" src={slic.boundaryDataUrl} />
{/if}
