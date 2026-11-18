<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import PointCloudAnnotationDetails from './PointCloudAnnotationDetails.svelte';
    import WorkspaceStoryProvider from '$lib/components/PointCloudLabelingWorkspace/WorkspaceStoryProvider';

    let {
        annotation,
        annotationSourceName,
        editable,
        occupiedTrackIds,
        onAnnotationChange,
        onTrackChange
    }: ComponentProps<typeof PointCloudAnnotationDetails> = $props();
</script>

<WorkspaceStoryProvider>
    <PointCloudAnnotationDetails
        {annotation}
        {annotationSourceName}
        {editable}
        {occupiedTrackIds}
        {onAnnotationChange}
        {onTrackChange}
    />
</WorkspaceStoryProvider>
