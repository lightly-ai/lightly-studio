<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog/index.js';
    import { Button } from '$lib/components/ui/button/index.js';
    import SelectList from '$lib/components/SelectList/SelectList.svelte';
    import type { ListItem } from '$lib/components/SelectList/types';

    type Props = {
        open: boolean;
        labels: string[];
        onConfirm: (label: string) => void;
        onCancel: () => void;
    };

    let { open = $bindable(false), labels, onConfirm, onCancel }: Props = $props();

    let selectedItem = $state<ListItem | undefined>(undefined);
    // Track close origin so the onOpenChange(false) that fires when we set
    // open = false from handleConfirm does not also invoke onCancel.
    let closedByConfirm = false;

    const items = $derived<ListItem[]>(
        [...new Set(labels)].sort((a, b) => a.localeCompare(b)).map((l) => ({ value: l, label: l }))
    );

    const handleConfirm = () => {
        if (selectedItem) {
            closedByConfirm = true;
            onConfirm(selectedItem.value);
            open = false;
            selectedItem = undefined;
        }
    };

    const handleCancel = () => {
        onCancel();
        open = false;
        selectedItem = undefined;
    };

    const handleOpenChange = (isOpen: boolean) => {
        if (isOpen) return;
        if (closedByConfirm) {
            closedByConfirm = false;
            return;
        }
        handleCancel();
    };
</script>

<Dialog.Root bind:open onOpenChange={handleOpenChange}>
    <Dialog.Content class="max-w-sm">
        <Dialog.Header>
            <Dialog.Title>Select a Class</Dialog.Title>
            <Dialog.Description>
                Choose an existing class or type a new one to create it.
            </Dialog.Description>
        </Dialog.Header>

        <div class="space-y-1 py-2">
            <SelectList
                bind:selectedItem
                {items}
                label="Select a class..."
                placeholder="Search or create a class..."
                className="w-full"
            />
        </div>

        <Dialog.Footer>
            <Button variant="outline" onclick={handleCancel}>Cancel</Button>
            <Button onclick={handleConfirm} disabled={!selectedItem}>Confirm</Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
