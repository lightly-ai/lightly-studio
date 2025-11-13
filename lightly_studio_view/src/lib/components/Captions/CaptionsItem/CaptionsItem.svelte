<script lang="ts">
    import type { SampleView } from '$lib/api/lightly_studio_local';
    import { SampleImage } from '$lib/components';
    import { useSettings } from '$lib/hooks/useSettings';

    const {
        item
    }: {
        item: SampleView;
    } = $props();

    const { gridViewSampleRenderingStore } = useSettings();

    let objectFit = $derived($gridViewSampleRenderingStore); // Use store value directly
    $inspect(item);
</script>

<div class="flex flex-row items-center gap-10">
    <SampleImage sample={item} {objectFit} />
    <div class="text-container flex-1 text-sm text-foreground">
        {#each item.captions.map((e) => e.text) as text}
            <p>{text}</p>
        {/each}
    </div>
</div>
