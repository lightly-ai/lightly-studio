<script lang="ts">
    import { Trash2 } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import * as Popover from '$lib/components/ui/popover';

    type Props = {
        selectedCount: number;
        disabled?: boolean;
        isLoading?: boolean;
        onDelete: () => Promise<void> | void;
    };

    let { selectedCount, disabled = false, isLoading = false, onDelete }: Props = $props();
    let open = $state(false);

    const handleDelete = async (event: MouseEvent) => {
        event.stopPropagation();
        await onDelete();
        open = false;
    };
</script>

<Popover.Root bind:open>
    <Popover.Trigger>
        {#snippet child({ props })}
            <Button
                variant="destructive"
                buttonProps={{
                    ...props,
                    disabled: disabled || isLoading || selectedCount === 0,
                    class: 'w-full',
                    'data-testid': 'bulk-delete-annotations-trigger'
                }}
                icon={Trash2}
            >
                Delete
            </Button>
        {/snippet}
    </Popover.Trigger>
    <Popover.Content class="w-72 text-sm">
        Delete {selectedCount}
        {selectedCount === 1 ? 'annotation' : 'annotations'}. This cannot be undone.
        <div class="mt-3 flex justify-end gap-2">
            <Button
                variant="outline"
                buttonProps={{
                    size: 'sm',
                    disabled: isLoading,
                    onclick: (event: MouseEvent) => {
                        event.stopPropagation();
                        open = false;
                    }
                }}
            >
                Cancel
            </Button>
            <Button
                variant="destructive"
                buttonProps={{
                    size: 'sm',
                    disabled: isLoading,
                    'data-testid': 'bulk-delete-annotations-confirm',
                    onclick: handleDelete
                }}
            >
                Delete
            </Button>
        </div>
    </Popover.Content>
</Popover.Root>
