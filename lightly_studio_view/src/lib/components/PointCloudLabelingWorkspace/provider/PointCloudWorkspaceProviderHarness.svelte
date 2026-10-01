<script lang="ts">
    import { createPointCloudWorkspaceContext } from './createPointCloudWorkspaceContext';
    import { usePointCloudWorkspaceContext } from './usePointCloudWorkspaceContext';
    import type { PointCloudWorkspaceContext } from './types';

    interface Props {
        datasetId: string;
        sequenceId: string;
        onReady: (result: {
            created: PointCloudWorkspaceContext;
            used: PointCloudWorkspaceContext;
        }) => void;
    }

    let { datasetId, sequenceId, onReady }: Props = $props();

    // create then use in the same component: setContext registers it, getContext reads it back.
    const created = createPointCloudWorkspaceContext(() => ({ datasetId, sequenceId }));
    const used = usePointCloudWorkspaceContext();

    $effect(() => {
        onReady({ created, used });
    });
</script>
