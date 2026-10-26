<script lang="ts">
    import PointCloudWorkspaceScene from './PointCloudWorkspaceScene.svelte';
    import { providePointCloudWorkspaceLayoutContext } from './pointCloudWorkspaceLayoutContext.svelte';
    import type { PointCloudWorkspaceLayoutState } from './pointCloudWorkspaceLayoutContext.svelte';

    /** Supplies reactive workspace state to the scene integration test. */
    interface Props {
        /** Scene data and actions provided by the workspace shell. */
        state: PointCloudWorkspaceLayoutState;
    }
    let { state }: Props = $props();
    providePointCloudWorkspaceLayoutContext(() => state);
</script>

<PointCloudWorkspaceScene />
