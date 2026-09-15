<script lang="ts">
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import WorkspaceStatusPanel from '$lib/components/PointCloudLabelingWorkspace/WorkspaceStatusPanel/WorkspaceStatusPanel.svelte';

    // MCAP collections have no dedicated gallery: a point-cloud sample is only reachable from a
    // specific sample_id, most often via a group component. Landing here directly (e.g. a stale
    // bookmark) has nothing useful to show, so send people back rather than rendering an empty grid.
    const handleExit = () => {
        void goto(routeHelpers.toHome());
    };
</script>

<div class="flex h-full min-h-0 w-full flex-1" data-testid="point-clouds-collection-route">
    <WorkspaceStatusPanel status="unsupported" onExit={handleExit} />
</div>
