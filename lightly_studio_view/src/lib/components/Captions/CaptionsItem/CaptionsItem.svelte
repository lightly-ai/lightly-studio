<script lang="ts">
    import type { CaptionDetailsView } from '$lib/api/lightly_studio_local';
    import { SampleImage } from '$lib/components';
    import { useSettings } from '$lib/hooks/useSettings';

    const {
        item
    }: {
        item: CaptionDetailsView;
    } = $props();

    const { gridViewSampleRenderingStore } = useSettings();

    let objectFit = $derived($gridViewSampleRenderingStore); // Use store value directly
    $inspect(item);
</script>

<div class="flex flex-row items-center gap-10">
    <SampleImage sample={item.sample} {objectFit} />
    <div class="text-container flex-1 text-sm text-foreground">{item.text}</div>
</div>

<style>
    .text-container {
        width: 100%;
        max-height: var(--max-height);
        overflow: scroll;
    }
</style>
