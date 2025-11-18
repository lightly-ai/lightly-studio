<script lang="ts">
    import { Card, CardContent } from '$lib/components';
    import type { SampleView } from '$lib/api/lightly_studio_local';
    import { SampleImage } from '$lib/components';
    import SampleDetailsSidePanelCaption from '$lib/components/SampleDetails/SampleDetailsSidePanel/SampleDetailsSidePanelCaption/SampleDetailsSidePanelCaption.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useSettings } from '$lib/hooks/useSettings';

    const {
        item,
        onUpdate,
        maxHeight = '100%'
    }: {
        item: SampleView;
        onUpdate: () => void;
        maxHeight?: string;
    } = $props();

    const { gridViewSampleRenderingStore } = useSettings();

    let objectFit = $derived($gridViewSampleRenderingStore); // Use store value directly
    $inspect(item);
    const captions = $derived(item.captions ?? []);
</script>

<div style={`height: ${maxHeight}; max-height: ${maxHeight};`}>
    <Card className="h-full">
        <CardContent className="h-full flex min-h-0 flex-row items-center dark:[color-scheme:dark]">
            <SampleImage sample={item} {objectFit} />
            <div class="flex h-full w-full flex-1 flex-col overflow-auto px-4 py-2">
                {#each item.captions as caption}
                    <SampleDetailsSidePanelCaption {caption} {onUpdate} />
                {/each}
            </div>
        </CardContent>
    </Card>
</div>
