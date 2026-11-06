<script lang="ts">
    import { trackClassCreatedInPicker } from '$lib/utils';
    import { useCanCreateAnnotationClass } from '$lib/hooks';
    import LabelNotFound from '$lib/components/LabelNotFound/LabelNotFound.svelte';
    import * as Dialog from '$lib/components/ui/dialog/index.js';
    import { Button } from '$lib/components';
    import SelectList from '$lib/components/SelectList/SelectList.svelte';
    import type { ListItem } from '$lib/components/SelectList/types';

    type Props = {
        open: boolean;
        labels: string[];
        onConfirm: (label: string) => void;
        onCancel: () => void;
    };

    let { open = $bindable(false), labels, onConfirm, onCancel }: Props = $props();

    const canCreateClass = useCanCreateAnnotationClass();

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

    const handleKeyboardConfirm = (item: ListItem) => {
        closedByConfirm = true;
        onConfirm(item.value);
        open = false;
        selectedItem = undefined;
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
                {canCreateClass
                    ? 'Choose an existing class or type a new one to create it.'
                    : 'Choose an existing class.'}
            </Dialog.Description>
        </Dialog.Header>

        <div class="min-w-0 space-y-1 py-2">
            <SelectList
                onCreate={trackClassCreatedInPicker}
                allowCreate={canCreateClass}
                bind:selectedItem
                {items}
                label="Select a class..."
                placeholder={canCreateClass ? 'Search or create a class...' : 'Search a class...'}
                className="w-full"
                autoOpen
                autoFocus
                onKeyboardConfirm={handleKeyboardConfirm}
            >
                {#snippet notFound({ inputValue })}
                    <LabelNotFound label={inputValue} canCreate={canCreateClass} />
                {/snippet}
            </SelectList>
        </div>

        <Dialog.Footer>
            <Button variant="outline" buttonProps={{ onclick: handleCancel }}>Cancel</Button>
            <Button
                variant="default"
                buttonProps={{ onclick: handleConfirm, disabled: !selectedItem }}
            >
                Confirm
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
