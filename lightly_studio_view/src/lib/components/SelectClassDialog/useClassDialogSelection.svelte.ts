import type { ListItem } from '$lib/components/SelectList/types';

interface UseClassDialogSelectionParams {
    getOpen: () => boolean;
    setOpen: (open: boolean) => void;
    /** The class selected when the dialog opens. */
    getInitialLabel: () => string | undefined;
    /** Whether the caller allows to confirm. */
    getCanConfirm: () => boolean;
    onConfirm: (label: string) => void;
    onCancel: () => void;
}

/** Holds the selected class of the class dialog and confirms or cancels it. */
export function useClassDialogSelection(params: UseClassDialogSelectionParams) {
    let selectedItem = $state<ListItem | undefined>(undefined);
    // Track close origin so the onOpenChange(false) that fires when we set
    // open = false from handleConfirm does not also invoke onCancel.
    let closedByConfirm = false;

    $effect(() => {
        const initialLabel = params.getInitialLabel();
        if (!params.getOpen() || !initialLabel || selectedItem) return;
        selectedItem = { value: initialLabel, label: initialLabel };
    });

    const confirmItem = (item: ListItem) => {
        selectedItem = item;
        if (!params.getCanConfirm()) return;
        closedByConfirm = true;
        params.onConfirm(item.value);
        params.setOpen(false);
        selectedItem = undefined;
    };

    const handleCancel = () => {
        params.onCancel();
        params.setOpen(false);
        selectedItem = undefined;
    };

    return {
        get selectedItem() {
            return selectedItem;
        },
        set selectedItem(item: ListItem | undefined) {
            selectedItem = item;
        },
        confirmItem,
        handleConfirm: () => {
            if (selectedItem) confirmItem(selectedItem);
        },
        handleCancel,
        handleOpenChange: (isOpen: boolean) => {
            if (isOpen) return;
            if (closedByConfirm) {
                closedByConfirm = false;
                return;
            }
            handleCancel();
        }
    };
}
