<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog';
    import { Button } from '$lib/components/ui/button';
    import { useAutoLabelDialog } from '$lib/hooks/useAutoLabelDialog';
    import { useGlobalStorage } from '$lib/hooks';
    import AutoLabelConfig from './AutoLabelConfig.svelte';

    const { isAutoLabelDialogOpen, closeAutoLabelDialog } = useAutoLabelDialog();
    const { filteredSampleCount } = useGlobalStorage();
    let task = $state<'object_detection' | 'segmentation'>('object_detection');
    let prompts = $state<string[]>([]);
    let overrides = $state<Record<string, string>>({});
    let threshold = $state(0.5);
</script>

<Dialog.Root
    open={$isAutoLabelDialogOpen}
    onOpenChange={(open) => {
        if (!open) closeAutoLabelDialog();
    }}
>
    <Dialog.Content class="max-h-[90vh] w-[calc(100%-2rem)] overflow-y-auto sm:max-w-[540px]">
        <Dialog.Header>
            <Dialog.Title>Auto-label images</Dialog.Title>
            <Dialog.Description>
                {$filteredSampleCount} images matching current filters
            </Dialog.Description>
        </Dialog.Header>
        <form onsubmit={(event) => event.preventDefault()} class="grid gap-5">
            <AutoLabelConfig bind:task bind:prompts bind:overrides bind:threshold />
            <p role="status" class="text-sm text-muted-foreground">Auto-labeling is coming soon.</p>
            <Dialog.Footer>
                <Button type="button" variant="outline" onclick={closeAutoLabelDialog}>
                    Cancel
                </Button>
                <Button type="submit" disabled>Auto-label</Button>
            </Dialog.Footer>
        </form>
    </Dialog.Content>
</Dialog.Root>
