<script lang="ts">
    import { createPointCloudWorkspaceContext } from './pointCloudWorkspaceContext.svelte';

    interface Props {
        datasetId: string;
        sequenceId: string;
        statusOverride?: 'loading' | 'unsupported' | 'empty' | 'error';
        onReady: (context: ReturnType<typeof createPointCloudWorkspaceContext>) => void;
    }

    let { datasetId, sequenceId, statusOverride, onReady }: Props = $props();

    const context = createPointCloudWorkspaceContext(() => ({
        datasetId,
        sequenceId,
        statusOverride
    }));

    $effect(() => {
        onReady(context);
    });
</script>
