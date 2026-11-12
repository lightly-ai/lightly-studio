<script lang="ts">
    import type { PointCloudWorkspaceContext } from '../provider/types';
    import type { WorkspaceOptions } from '../workspaceOptions';
    import { useWorkspacePlayback } from './useWorkspacePlayback.svelte';

    interface Props {
        workspace: PointCloudWorkspaceContext;
        options: WorkspaceOptions;
        onReady: (playback: ReturnType<typeof useWorkspacePlayback>) => void;
    }

    let { workspace, options, onReady }: Props = $props();
    const playback = useWorkspacePlayback(
        () => workspace,
        () => options
    );
    $effect(() => onReady(playback));
</script>
