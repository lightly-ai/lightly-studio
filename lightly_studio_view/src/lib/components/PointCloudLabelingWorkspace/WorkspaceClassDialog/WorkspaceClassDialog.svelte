<script lang="ts">
    import { untrack } from 'svelte';
    import { SelectClassDialog } from '$lib/components';
    import { useWorkspaceControllerContext } from '../pointCloudWorkspaceLayoutContext.svelte';
    import { CuboidSourceSection } from './CuboidSourceSection';

    const { editing, data, targetSource } = useWorkspaceControllerContext();
    const { showSelectClassDialog } = editing;

    // The source chosen in the dialog. It is applied only on confirm.
    let draftSource = $state<{ name: string; isNew: boolean } | null>(null);

    $effect(() => {
        if (!$showSelectClassDialog) return;
        untrack(() => {
            const name = targetSource.targetSource;
            draftSource = name ? { name, isNew: name === targetSource.typedSource } : null;
        });
    });

    function confirm(label: string) {
        if (draftSource) targetSource.setTarget(draftSource.name, { isNew: draftSource.isNew });
        editing.handleClassSelected(label);
    }
</script>

<SelectClassDialog
    bind:open={$showSelectClassDialog}
    labels={editing.labels.data
        ?.map((label) => label.annotation_label_name ?? '')
        .filter(Boolean) ?? []}
    onConfirm={confirm}
    onCancel={editing.handleClassDialogCancel}
    canConfirm={draftSource !== null}
    initialLabel={$showSelectClassDialog ? editing.getRememberedLabel() : undefined}
>
    {#snippet extra()}
        <CuboidSourceSection
            sourceNames={data.annotationSourceNames ?? []}
            selected={draftSource}
            onSelect={(choice) => (draftSource = choice)}
        />
    {/snippet}
</SelectClassDialog>
