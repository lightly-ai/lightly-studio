<script lang="ts">
    import { usePointCloudWorkspaceContext } from './usePointCloudWorkspaceContext';

    // No provider ancestor: the hook must throw during init rather than return undefined.
    usePointCloudWorkspaceContext();
</script>
