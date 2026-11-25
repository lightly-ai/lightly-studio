<script lang="ts">
    import { untrack } from 'svelte';
    import { SelectClassDialog } from '$lib/components';
    import { useWorkspaceControllerContext } from '../pointCloudWorkspaceLayoutContext.svelte';
    import { CuboidSourceSection } from './CuboidSourceSection';

    const controller = useWorkspaceControllerContext();
    const { editing, data, targetSource } = controller;
    const { showSelectClassDialog } = editing;
    type TrackSelection = Parameters<typeof editing.handleClassSelected>[1];
    const getCollectionId = () => controller.options.annotationSourceCollectionId;

    // The source chosen in the dialog. It is applied only on confirm.
    let draftSource = $state<{ name: string; isNew: boolean } | null>(null);
    let openedForCollectionId: string | undefined;

    $effect(() => {
        if (!$showSelectClassDialog) return;
        untrack(() => {
            openedForCollectionId = getCollectionId();
            const name = targetSource.targetSource;
            draftSource = name ? { name, isNew: name === targetSource.typedSource } : null;
        });
    });

    // Another tab can delete the drafted source while the dialog is open.
    const validDraftSource = $derived.by(() => {
        const names = data.annotationSourceNames ?? [];
        const isValid = draftSource && (draftSource.isNew || names.includes(draftSource.name));
        return isValid ? draftSource : null;
    });

    function confirm(label: string, track?: TrackSelection) {
        if (getCollectionId() !== openedForCollectionId) {
            editing.handleClassDialogCancel();
            return;
        }
        if (validDraftSource) {
            targetSource.setTarget(validDraftSource.name, { isNew: validDraftSource.isNew });
        }
        editing.handleClassSelected(label, track);
    }
</script>

<SelectClassDialog
    bind:open={$showSelectClassDialog}
    labels={editing.labels.data
        ?.map((label) => label.annotation_label_name ?? '')
        .filter(Boolean) ?? []}
    onConfirm={confirm}
    onCancel={editing.handleClassDialogCancel}
    canConfirm={validDraftSource !== null}
    initialLabel={$showSelectClassDialog ? editing.getRememberedLabel() : undefined}
    showTrackSelect
    tracks={editing.tracks.data ?? []}
    occupiedTrackIds={editing.occupiedTrackIds}
>
    {#snippet extra()}
        <CuboidSourceSection
            sourceNames={data.annotationSourceNames ?? []}
            selected={validDraftSource}
            onSelect={(choice) => (draftSource = choice)}
        />
    {/snippet}
</SelectClassDialog>
