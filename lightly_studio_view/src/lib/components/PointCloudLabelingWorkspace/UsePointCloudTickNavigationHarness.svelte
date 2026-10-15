<script lang="ts">
    import type { PointCloudWorkspaceContext } from './provider/types';
    import { usePointCloudTickNavigation } from './usePointCloudTickNavigation.svelte';

    interface Props {
        workspace: PointCloudWorkspaceContext;
        tickNumber: number;
        isTickBuffered?: (index: number) => boolean;
        onReady: (result: ReturnType<typeof usePointCloudTickNavigation>) => void;
    }

    let { workspace, tickNumber, isTickBuffered = () => true, onReady }: Props = $props();

    const navigation = usePointCloudTickNavigation({
        getWorkspace: () => workspace,
        getTickNumber: () => tickNumber,
        getOnTickChange: () => () => undefined,
        getIsTickBuffered: (index) => isTickBuffered(index)
    });

    $effect(() => onReady(navigation));
</script>
