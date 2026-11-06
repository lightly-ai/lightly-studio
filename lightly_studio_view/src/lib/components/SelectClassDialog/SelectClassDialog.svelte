<script lang="ts">
    import { trackClassCreatedInPicker } from '$lib/utils';
    import { useCanCreateAnnotationClass } from '$lib/hooks';
    import { LabelNotFound } from '$lib/components/LabelNotFound';
    import * as Dialog from '$lib/components/ui/dialog/index.js';
    import { Button } from '$lib/components';
    import { SelectList } from '$lib/components/SelectList';
    import type { ComponentProps } from 'svelte';
    import type { TrackWithClassNameView } from '$lib/api/lightly_studio_local';
    import { TrackSelect } from '$lib/components/TrackSelect';
    import { useClassDialogForm } from './useClassDialogForm/useClassDialogForm';

    interface Props {
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
    }

    let {
        open = $bindable(false),
        labels,
        onConfirm,
        onCancel,
        showTrackSelect = false,
        tracks = [],
        occupiedTrackIds = new Set()
    }: Props = $props();

    const canCreateClass = useCanCreateAnnotationClass();

    const availableTracks = $derived(
        tracks.filter((t) => !occupiedTrackIds.has(t.object_track_id))
    );

    const items = $derived<ComponentProps<typeof SelectList>['items']>(
        [...new Set(labels)].sort((a, b) => a.localeCompare(b)).map((l) => ({ value: l, label: l }))
    );
    const {
        selectedItem,
        trackValue,
        handleConfirm,
        handleCancel,
        handleOpenChange,
        handleClassSelect,
        handleTrackValueChange,
        handleKeyboardConfirm
    } = useClassDialogForm(() => ({
        onConfirm,
        onCancel,
        showTrackSelect,
        onClose: () => {
            open = false;
        }
    }));
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
                bind:selectedItem={$selectedItem}
                {items}
                label="Select a class..."
                placeholder={canCreateClass ? 'Search or create a class...' : 'Search a class...'}
                className="w-full"
                autoOpen
                autoFocus
                onKeyboardConfirm={handleKeyboardConfirm}
                onSelect={handleClassSelect}
            >
                {#snippet notFound({ inputValue })}
                    <LabelNotFound label={inputValue} allowCreate={canCreateClass} />
                {/snippet}
            </SelectList>
        </div>

        {#if showTrackSelect}
            <div class="min-w-0 space-y-1">
                <span class="text-sm font-medium text-muted-foreground">Track</span>
                <TrackSelect
                    tracks={availableTracks}
                    bind:value={$trackValue}
                    className="w-full"
                    onValueChange={handleTrackValueChange}
                />
            </div>
        {/if}

        <Dialog.Footer>
            <Button variant="outline" buttonProps={{ onclick: handleCancel }}>Cancel</Button>
            <Button
                variant="default"
                buttonProps={{ onclick: handleConfirm, disabled: !$selectedItem }}
            >
                Confirm
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
