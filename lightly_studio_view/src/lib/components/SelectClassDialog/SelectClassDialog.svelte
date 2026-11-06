<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog/index.js';
    import { Button } from '$lib/components';
    import SelectList from '$lib/components/SelectList/SelectList.svelte';
    import type { ListItem } from '$lib/components/SelectList/types';
    import type { TrackWithClassNameView } from '$lib/api/lightly_studio_local';
    import { TrackSelect } from '$lib/components/TrackSelect';

    type Props = {
        open: boolean;
        labels: string[];
        onConfirm: (
            label: string,
            track?: { objectTrackId: string | null; isNewTrack: boolean }
        ) => void;
        onCancel: () => void;
        showTrackSelect?: boolean;
        tracks?: TrackWithClassNameView[];
        /** Track IDs already assigned to annotations on the current frame. */
        occupiedTrackIds?: ReadonlySet<string>;
    };

    type TrackSelection = NonNullable<Parameters<Props['onConfirm']>[1]>;

    let {
        open = $bindable(false),
        labels,
        onConfirm,
        onCancel,
        showTrackSelect = false,
        tracks = [],
        occupiedTrackIds = new Set()
    }: Props = $props();

    const availableTracks = $derived(
        tracks.filter((t) => !occupiedTrackIds.has(t.object_track_id))
    );

    let selectedItem = $state<ListItem | undefined>(undefined);
    let previousClassValue = $state<string | undefined>(undefined);
    let trackValue = $state('__no_track__');
    let trackSelection = $state<TrackSelection>({ objectTrackId: null, isNewTrack: false });
    // Track close origin so the onOpenChange(false) that fires when we set
    // open = false from handleConfirm does not also invoke onCancel.
    let closedByConfirm = false;

    const items = $derived<ListItem[]>(
        [...new Set(labels)].sort((a, b) => a.localeCompare(b)).map((l) => ({ value: l, label: l }))
    );

    function resetTrack() {
        trackValue = '__no_track__';
        trackSelection = { objectTrackId: null, isNewTrack: false };
        previousClassValue = undefined;
    }

    function confirmWith(label: string) {
        closedByConfirm = true;
        if (showTrackSelect) {
            onConfirm(label, trackSelection);
        } else {
            onConfirm(label);
        }
        open = false;
        selectedItem = undefined;
        resetTrack();
    }

    const handleConfirm = () => {
        if (selectedItem) {
            confirmWith(selectedItem.value);
        }
    };

    const handleKeyboardConfirm = (item: ListItem) => {
        confirmWith(item.value);
    };

    const handleCancel = () => {
        onCancel();
        open = false;
        selectedItem = undefined;
        resetTrack();
    };

    const handleOpenChange = (isOpen: boolean) => {
        if (isOpen) return;
        if (closedByConfirm) {
            closedByConfirm = false;
            return;
        }
        handleCancel();
    };

    const handleClassSelect = (item: ListItem) => {
        if (previousClassValue !== item.value) {
            resetTrack();
        }
        previousClassValue = item.value;
    };

    const handleTrackValueChange = (objectTrackId: string | null, isNewTrack: boolean) => {
        trackSelection = { objectTrackId, isNewTrack };
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

        <div class="min-w-0 space-y-1 py-2">
            <SelectList
                bind:selectedItem
                {items}
                label="Select a class..."
                placeholder="Search or create a class..."
                className="w-full"
                autoOpen
                autoFocus
                onKeyboardConfirm={handleKeyboardConfirm}
                onSelect={handleClassSelect}
            />
        </div>

        {#if showTrackSelect}
            <div class="min-w-0 space-y-1">
                <span class="text-sm font-medium text-muted-foreground">Track</span>
                <TrackSelect
                    tracks={availableTracks}
                    bind:value={trackValue}
                    className="w-full"
                    onValueChange={handleTrackValueChange}
                />
            </div>
        {/if}

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
