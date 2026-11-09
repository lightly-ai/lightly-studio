<script lang="ts">
    import ZoomableContainer from './ZoomableContainer.svelte';

    let {
        boundingBox,
        autoFocusEnabled = true,
        autoFocusKey,
        panEnabled = true,
        zoomEnabled = true
    }: {
        boundingBox?: { x: number; y: number; width: number; height: number };
        autoFocusEnabled?: boolean;
        autoFocusKey?: string;
        panEnabled?: boolean;
        zoomEnabled?: boolean;
    } = $props();
</script>

<div class="h-[600px] w-[800px]">
    <ZoomableContainer
        width={1000}
        height={800}
        {boundingBox}
        {autoFocusEnabled}
        {autoFocusKey}
        {panEnabled}
        {zoomEnabled}
    >
        {#snippet zoomableContent()}
            <rect width="1000" height="800" fill="transparent" />
        {/snippet}
    </ZoomableContainer>
</div>
