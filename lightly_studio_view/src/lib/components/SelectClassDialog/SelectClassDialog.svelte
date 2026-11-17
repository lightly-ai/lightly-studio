<script lang="ts">
    import { trackClassCreatedInPicker } from '$lib/utils';
    import { useCanCreateAnnotationClass } from '$lib/hooks';
    import { LabelNotFound } from '$lib/components/LabelNotFound';
    import * as Dialog from '$lib/components/ui/dialog/index.js';
    import { Button } from '$lib/components';
    import SelectList from '$lib/components/SelectList/SelectList.svelte';
    import type { ListItem } from '$lib/components/SelectList/types';
    import type { Snippet } from 'svelte';
    import { useClassDialogSelection } from './useClassDialogSelection.svelte';

    type Props = {
        open: boolean;
        labels: string[];
        onConfirm: (label: string) => void;
        onCancel: () => void;
        /** Content above the class list. With it, the list does not open by itself and cover it. */
        extra?: Snippet;
        /** Whether the caller allows to confirm, for example after its extra fields are set. */
        canConfirm?: boolean;
        /** The class selected when the dialog opens. */
        initialLabel?: string;
    };

    let {
        open = $bindable(false),
        labels,
        onConfirm,
        onCancel,
        extra,
        canConfirm = true,
        initialLabel
    }: Props = $props();

    const canCreateClass = useCanCreateAnnotationClass();

    const selection = useClassDialogSelection({
        getOpen: () => open,
        setOpen: (isOpen) => (open = isOpen),
        getInitialLabel: () => initialLabel,
        getCanConfirm: () => canConfirm,
        onConfirm: (label) => onConfirm(label),
        onCancel: () => onCancel()
    });

    const items = $derived<ListItem[]>(
        [...new Set(labels)].sort((a, b) => a.localeCompare(b)).map((l) => ({ value: l, label: l }))
    );
</script>

<Dialog.Root bind:open onOpenChange={selection.handleOpenChange}>
    <Dialog.Content class="max-w-sm">
        <Dialog.Header>
            <Dialog.Title>Select a Class</Dialog.Title>
            <Dialog.Description>
                {canCreateClass
                    ? 'Choose an existing class or type a new one to create it.'
                    : 'Choose an existing class.'}
            </Dialog.Description>
        </Dialog.Header>

        {@render extra?.()}
        <div class="min-w-0 space-y-1 py-2">
            <SelectList
                onCreate={trackClassCreatedInPicker}
                allowCreate={canCreateClass}
                bind:selectedItem={selection.selectedItem}
                {items}
                label="Select a class..."
                placeholder={canCreateClass ? 'Search or create a class...' : 'Search a class...'}
                className="w-full"
                autoOpen={!extra}
                autoFocus
                onKeyboardConfirm={selection.confirmItem}
            >
                {#snippet notFound({ inputValue })}
                    <LabelNotFound label={inputValue} allowCreate={canCreateClass} />
                {/snippet}
            </SelectList>
        </div>

        <Dialog.Footer>
            <Button variant="outline" buttonProps={{ onclick: selection.handleCancel }}
                >Cancel</Button
            >
            <Button
                variant="default"
                buttonProps={{
                    onclick: selection.handleConfirm,
                    disabled: !selection.selectedItem || !canConfirm
                }}
            >
                Confirm
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
