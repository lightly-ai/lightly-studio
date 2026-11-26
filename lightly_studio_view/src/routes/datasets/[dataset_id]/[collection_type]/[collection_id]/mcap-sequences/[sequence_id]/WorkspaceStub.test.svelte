<script lang="ts">
    import type { WorkspaceOptions } from '$lib/components/PointCloudLabelingWorkspace/workspaceOptions';

    type Props = Pick<
        WorkspaceOptions,
        'tickNumber' | 'openCamera' | 'onTickChange' | 'onOpenCameraChange'
    >;

    const { tickNumber, openCamera, onTickChange, onOpenCameraChange }: Props = $props();
</script>

<p data-testid="workspace-hash-state">tick {tickNumber}, camera {openCamera ?? 'none'}</p>
<button type="button" onclick={() => onTickChange?.(5)}>Go to tick 5</button>
<button type="button" onclick={() => onOpenCameraChange?.('CAM_B', 'push')}>Open CAM_B</button>
