<script lang="ts">
    import * as Popover from '$lib/components/ui/popover/index.js';
    import type { Snippet } from 'svelte';
    import Button from '../ui/button/button.svelte';

    const { children, onDelete }: { children: Snippet; onDelete: (e: MouseEvent) => void } =
        $props();

    let showDeleteConfirmation = $state(false);
</script>

<Popover.Root bind:open={showDeleteConfirmation}>
    <Popover.Trigger>
        {@render children()}
    </Popover.Trigger>
    <Popover.Content>
        You are going to delete this annotation. This action cannot be undone.
        <div class="mt-2 flex justify-end gap-2">
            <Button
                variant="destructive"
                size="sm"
                data-testid="confirm-delete-annotation"
                onclick={(e: MouseEvent) => {
                    e.stopPropagation();
                    onDelete(e);
                    showDeleteConfirmation = false;
                }}>Delete</Button
            >
            <Button
                variant="outline"
                size="sm"
                onclick={(e: MouseEvent) => {
                    e.stopPropagation();
                    showDeleteConfirmation = false;
                }}>Cancel</Button
            >
        </div>
    </Popover.Content>
</Popover.Root>
