<script lang="ts">
    import { page } from '$app/state';
    import { Card, CardContent } from '$lib/components';
    import type { SampleView } from '$lib/api/lightly_studio_local';
    import { SampleImage } from '$lib/components';
    import CaptionField from '$lib/components/CaptionField/CaptionField.svelte';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useCreateCaption } from '$lib/hooks/useCreateCaption/useCreateCaption';
    import { toast } from 'svelte-sonner';

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
    const { isEditingMode } = page.data.globalStorage;

    let objectFit = $derived($gridViewSampleRenderingStore); // Use store value directly
    $inspect(item);

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
</script>

<div style={`height: ${maxHeight}; max-height: ${maxHeight};`}>
    <Card className="h-full">
        <CardContent className="h-full flex min-h-0 flex-row items-center dark:[color-scheme:dark]">
            <SampleImage sample={item} {objectFit} />
            <div class="flex h-full w-full flex-1 flex-col overflow-auto px-4 py-2">
                {#each item.captions as caption}
                    <CaptionField {caption} {onUpdate} />
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
