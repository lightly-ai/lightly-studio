import { get, writable } from 'svelte/store';
import type { ComponentProps } from 'svelte';
import { SelectList } from '$lib/components/SelectList';
import type { useSelectClassDialog } from '$lib/hooks';

type ListItem = ComponentProps<typeof SelectList>['items'][number];
type OnConfirm = ReturnType<typeof useSelectClassDialog>['handleConfirm'];
type TrackSelection = NonNullable<Parameters<OnConfirm>[1]>;

interface Options {
    onConfirm: OnConfirm;
    onCancel: () => void;
    onClose: () => void;
    showTrackSelect: boolean;
    /** Whether the caller allows to confirm, for example after its extra fields are set. */
    canConfirm?: boolean;
}

export function useClassDialogForm(getOptions: () => Options) {
    const selectedItem = writable<ListItem | undefined>(undefined);
    const trackValue = writable('__no_track__');
    let trackSelection: TrackSelection = { objectTrackId: null, isNewTrack: false };
    let previousClassValue: string | undefined;
    // Confirming also closes the dialog; ignore the resulting close notification.
    let closedByConfirm = false;

    function resetTrack() {
        trackValue.set('__no_track__');
        trackSelection = { objectTrackId: null, isNewTrack: false };
        previousClassValue = undefined;
    }

    function close() {
        selectedItem.set(undefined);
        resetTrack();
        getOptions().onClose();
    }

    function confirmWith(label: string) {
        if (getOptions().canConfirm === false) return;
        closedByConfirm = true;
        const { onConfirm, showTrackSelect } = getOptions();
        if (showTrackSelect) onConfirm(label, trackSelection);
        else onConfirm(label);
        close();
        // Bits UI does not fire onOpenChange on programmatic close (bind:open),
        // so reset the flag here to prevent it from staying stale.
        closedByConfirm = false;
    }

    function handleConfirm() {
        const item = get(selectedItem);
        if (item) confirmWith(item.value);
    }

    function handleCancel() {
        getOptions().onCancel();
        close();
    }

    function handleOpenChange(isOpen: boolean) {
        if (isOpen) return;
        if (closedByConfirm) {
            closedByConfirm = false;
            return;
        }
        handleCancel();
    }

    function handleClassSelect(item: ListItem) {
        if (previousClassValue !== item.value) resetTrack();
        previousClassValue = item.value;
    }

    function handleTrackValueChange(objectTrackId: string | null, isNewTrack: boolean) {
        trackSelection = { objectTrackId, isNewTrack };
    }

    return {
        selectedItem,
        trackValue,
        handleConfirm,
        handleCancel,
        handleOpenChange,
        handleClassSelect,
        handleTrackValueChange,
        /** Selects the class the dialog opens with, unless the user already picked one. */
        preselect: (label: string | undefined) => {
            if (label && !get(selectedItem)) selectedItem.set({ value: label, label });
        },
        handleKeyboardConfirm: (item: ListItem) => {
            const { showTrackSelect, canConfirm } = getOptions();
            if (showTrackSelect || canConfirm === false) {
                selectedItem.set(item);
                return;
            }
            confirmWith(item.value);
        }
    };
}
