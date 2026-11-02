<script lang="ts">
    import { SelectClassDialog } from '$lib/components';
    import { useWorkspaceControllerContext } from '../pointCloudWorkspaceLayoutContext.svelte';
    const { editing } = useWorkspaceControllerContext();
    const { showSelectClassDialog } = editing;
</script>

<SelectClassDialog
    bind:open={$showSelectClassDialog}
    labels={editing.labels.data
        ?.map((label) => label.annotation_label_name ?? '')
        .filter(Boolean) ?? []}
    onConfirm={editing.handleClassSelected}
    onCancel={editing.handleClassDialogCancel}
/>
