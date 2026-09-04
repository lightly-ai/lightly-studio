<script lang="ts">
    import { Info } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import * as Alert from '$lib/components/ui/alert';
    import * as Dialog from '$lib/components/ui/dialog';
    import CreateableNamePicker from './CreateableNamePicker.svelte';

    type Props = {
        selectedCount: number;
        sourceName?: string;
        className?: string;
        sourceNames: string[];
        classNames: string[];
        isApplying?: boolean;
        onSourceSelect: (name: string) => void;
        onClassSelect: (name: string) => void;
        onApply: () => Promise<void> | void;
    };

    let {
        selectedCount,
        sourceName,
        className,
        sourceNames,
        classNames,
        isApplying = false,
        onSourceSelect,
        onClassSelect,
        onApply
    }: Props = $props();

    let confirmOpen = $state(false);
    const canApply = $derived(Boolean(sourceName && className) && !isApplying);
    const heading = $derived(
        `${selectedCount} ${selectedCount === 1 ? 'image' : 'images'} selected`
    );

    async function handleConfirm() {
        await onApply();
        confirmOpen = false;
    }
</script>

<div class="h-full overflow-hidden border-l bg-background p-3 dark:[color-scheme:dark]">
    <div class="flex h-full min-h-0 w-[260px] flex-col gap-4 overflow-hidden">
        <h2 class="text-sm font-semibold">{heading}</h2>
        <CreateableNamePicker
            label="Source"
            placeholder="Select a source"
            selectedName={sourceName}
            names={sourceNames}
            disabled={isApplying}
            onSelect={onSourceSelect}
        />
        <CreateableNamePicker
            label="Class"
            placeholder="Select a class"
            selectedName={className}
            names={classNames}
            disabled={isApplying}
            onSelect={onClassSelect}
        />
        <Dialog.Root bind:open={confirmOpen}>
            <Dialog.Trigger>
                {#snippet child({ props })}
                    <Button {...props} class="w-full" disabled={!canApply}>Add class</Button>
                {/snippet}
            </Dialog.Trigger>
            <Dialog.Content class="max-w-sm">
                <Dialog.Header>
                    <Dialog.Title>Add class</Dialog.Title>
                    <Dialog.Description>
                        Add <strong>{className}</strong> to {selectedCount}
                        {selectedCount === 1 ? ' image ' : ' images '} in
                        <strong>{sourceName}</strong>. This cannot be undone.
                    </Dialog.Description>
                </Dialog.Header>
                <Dialog.Footer>
                    <Dialog.Close>
                        {#snippet child({ props })}
                            <Button {...props} variant="outline" disabled={isApplying}>
                                Cancel
                            </Button>
                        {/snippet}
                    </Dialog.Close>
                    <Button disabled={isApplying} onclick={handleConfirm}>Add class</Button>
                </Dialog.Footer>
            </Dialog.Content>
        </Dialog.Root>
        <Alert.Root class="bg-muted/50 py-3 text-xs">
            <Info class="size-3.5" />
            <Alert.Description>
                Change or remove annotations in the annotation view.
            </Alert.Description>
        </Alert.Root>
    </div>
</div>
