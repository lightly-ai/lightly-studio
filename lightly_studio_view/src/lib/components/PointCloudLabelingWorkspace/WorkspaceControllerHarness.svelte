<script lang="ts">
    import { setQueryClientContext, type QueryClient } from '@tanstack/svelte-query';
    import { untrack } from 'svelte';
    import { createWorkspaceController } from './createWorkspaceController.svelte';

    interface Props {
        client: QueryClient;
    }

    const { client }: Props = $props();
    setQueryClientContext(untrack(() => client));
    const controller = createWorkspaceController(() => ({
        datasetId: 'dataset-1',
        sequenceId: 'sequence-1'
    }));
</script>

<p>Ticks: {controller.workspace.ticks.length}</p>

<p>Points: {controller.workspace.cloudPointFrame.data?.batch.count ?? 0}</p>
