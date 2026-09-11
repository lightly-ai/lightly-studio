<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { Card, CardContent, Segment } from '$lib/components';
    import * as Dialog from '$lib/components/ui/dialog';
    import NamePickerField from './NamePickerField.svelte';

    interface Props {
        selectedCount: number;
        sourceName?: string;
        className?: string;
        sourceNames: string[];
        classNames: string[];
        isApplying?: boolean;
        onSourceSelect: (name: string) => void;
        onClassSelect: (name: string) => void;
        onApply: () => Promise<void> | void;
    }

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
    const canApply = $derived(Boolean(sourceName && className) && selectedCount > 0 && !isApplying);

    async function handleConfirm() {
        try {
            await onApply();
        } catch {
            // onApply reports its own failures.
        }
        confirmOpen = false;
    }
</script>

<Card className="h-full">
    <CardContent className="h-full flex flex-col">
        <div
            class="flex h-full min-h-0 flex-col space-y-4 overflow-hidden dark:[color-scheme:dark]"
        >
            <Segment title={`Selected images: ${selectedCount}`}>
                <div class="flex flex-col space-y-4">
                    <NamePickerField
                        label="Annotation source"
                        placeholder="Select an annotation source"
                        selectedName={sourceName}
                        names={sourceNames}
                        disabled={isApplying}
                        onSelect={onSourceSelect}
                    />
                    <NamePickerField
                        label="Annotation class"
                        placeholder="Select an annotation class"
                        selectedName={className}
                        names={classNames}
                        disabled={isApplying}
                        onSelect={onClassSelect}
                    />
                    <Dialog.Root bind:open={confirmOpen}>
                        <Dialog.Trigger>
                            {#snippet child({ props })}
                                <Button {...props} class="w-full" disabled={!canApply}
                                    >Add annotation class</Button
                                >
                            {/snippet}
                        </Dialog.Trigger>
                        <Dialog.Content class="max-w-sm">
                            <Dialog.Header>
                                <Dialog.Title>Add annotation class</Dialog.Title>
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
                                <Button disabled={isApplying} onclick={handleConfirm}
                                    >Add annotation class</Button
                                >
                            </Dialog.Footer>
                        </Dialog.Content>
                    </Dialog.Root>
                </div>
            </Segment>
        </div>
    </CardContent>
</Card>
