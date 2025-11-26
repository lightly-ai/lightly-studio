<script lang="ts">
    import { goto } from '$app/navigation';
    import { toast } from 'svelte-sonner';
    import { page } from '$app/state';
    import { Card, CardContent } from '$lib/components';
    import type { SampleView } from '$lib/api/lightly_studio_local';
    import { SampleImage } from '$lib/components';
    import CaptionField from '$lib/components/CaptionField/CaptionField.svelte';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useDeleteCaption } from '$lib/hooks/useDeleteCaption/useDeleteCaption';
    import { useCreateCaption } from '$lib/hooks/useCreateCaption/useCreateCaption';
    import { routeHelpers } from '$lib/routes';

    const {
        item,
        onUpdate,
        datasetId,
        sampleIndex,
        maxHeight = '100%'
    }: {
        item: SampleView;
        onUpdate: () => void;
        datasetId: string;
        sampleIndex: number;
        maxHeight?: string;
    } = $props();

    const { gridViewSampleRenderingStore } = useSettings();
    const { isEditingMode } = page.data.globalStorage;

    let objectFit = $derived($gridViewSampleRenderingStore); // Use store value directly
    $inspect(item);

    const { deleteCaption } = useDeleteCaption();

    const onDeleteCaption = async (sampleId: string) => {
        if (!item) return;

        try {
            await deleteCaption(sampleId);
            toast.success('Caption deleted successfully');
            onUpdate();
        } catch (error) {
            toast.error('Failed to delete caption. Please try again.');
            console.error('Error deleting caption:', error);
        }
    };

    const { createCaption } = useCreateCaption();

    const onCreateCaption = async (sampleId: string) => {
        try {
            await createCaption({ parent_sample_id: sampleId });
            toast.success('Caption created successfully');
            onUpdate();
        } catch (error) {
            toast.error('Failed to create caption. Please try again.');
            console.error('Error creating caption:', error);
        }
    };

    const handleOnDoubleClick = () => {
        goto(
            routeHelpers.toSample({
                sampleId: item.sample_id,
                datasetId,
                sampleIndex
            })
        );
    };
</script>

<div style={`height: ${maxHeight}; max-height: ${maxHeight};`}>
    <Card className="h-full">
        <CardContent className="h-full flex min-h-0 flex-row items-center dark:[color-scheme:dark]">
            <div
                class="sample-visual cursor-pointer"
                ondblclick={handleOnDoubleClick}
                aria-label="Open sample details"
                role="button"
                tabindex="0"
            >
                <SampleImage sample={item} {objectFit} />
            </div>
            <div class="flex h-full w-full flex-1 flex-col overflow-auto px-4 py-2">
                {#each item.captions as caption}
                    <CaptionField
                        {caption}
                        onDeleteCaption={() => onDeleteCaption(caption.sample_id)}
                        {onUpdate}
                    />
                {/each}
                {#if $isEditingMode}
                    <button
                        type="button"
                        class="mb-2 flex h-8 items-center justify-center rounded-sm bg-card px-2 py-0 text-diffuse-foreground transition-colors hover:bg-primary hover:text-primary-foreground"
                        onclick={() => onCreateCaption(item.sample_id)}
                    >
                        +
                    </button>
                {/if}
            </div>
        </CardContent>
    </Card>
</div>
