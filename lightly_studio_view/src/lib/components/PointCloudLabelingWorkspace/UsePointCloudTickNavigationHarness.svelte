<script lang="ts">
    import type { PointCloudWorkspaceContext } from './provider/types';
    import { usePointCloudTickNavigation } from './usePointCloudTickNavigation.svelte';

    interface Props {
        workspace: PointCloudWorkspaceContext;
        tickNumber: number;
        onReady: (result: ReturnType<typeof usePointCloudTickNavigation>) => void;
    }

    let { workspace, tickNumber, onReady }: Props = $props();

    const navigation = usePointCloudTickNavigation({
        getWorkspace: () => workspace,
        getTickNumber: () => tickNumber,
        getOnTickChange: () => () => undefined
    });

    $effect(() => onReady(navigation));
</script>
