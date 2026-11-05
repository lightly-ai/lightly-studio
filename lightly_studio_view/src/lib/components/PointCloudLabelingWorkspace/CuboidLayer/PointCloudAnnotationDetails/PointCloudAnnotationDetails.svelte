<script lang="ts">
    import { createAnnotationDetails } from './pointCloudAnnotationDetails';
    import { useAnnotationDetailsEditing } from './useAnnotationDetailsEditing.svelte';
    import AnnotationGeometryGroup from './AnnotationGeometryGroup';
    import { Typography } from '$lib/components/Typography';
    import TrackSelect from '$lib/components/TrackSelect/TrackSelect.svelte';
    import { useTracks, useUpdateAnnotationsMutation } from '$lib/hooks';
    import { usePointCloudWorkspaceLayoutContext } from '$lib/components/PointCloudLabelingWorkspace/pointCloudWorkspaceLayoutContext.svelte';

    type AnnotationInput = Parameters<typeof createAnnotationDetails>[0]['annotation'] & {
        id: string;
        trackId: string | null;
        annotationSourceId: string;
    };

    interface Props {
        /** Cuboid whose metadata is displayed. */
        annotation: AnnotationInput;
        /** Human-readable annotation source name, when available. */
        annotationSourceName?: string;
        /** When true, numeric fields become editable inputs. */
        editable?: boolean;
        /** Called with the full updated annotation when a field is committed. */
        onAnnotationChange?: (annotation: AnnotationInput) => void;
        /** Called after the annotation's track assignment changes. */
        onTrackChange?: () => void;
    }

    let {
        annotation,
        annotationSourceName,
        editable = false,
        onAnnotationChange,
        onTrackChange
    }: Props = $props();
    const details = $derived(createAnnotationDetails({ annotation, annotationSourceName }));
    const editing = useAnnotationDetailsEditing(
        () => annotation,
        (updated) => onAnnotationChange?.(updated)
    );

    const getLayoutState = usePointCloudWorkspaceLayoutContext();
    const tracksQuery = useTracks(() => getLayoutState().datasetId);
    const tracks = $derived(tracksQuery.data ?? []);

    const { updateAnnotations } = useUpdateAnnotationsMutation({
        getCollectionId: () => annotation.annotationSourceId
    });

    async function handleTrackChange(trackId: string | null, isNewTrack: boolean) {
        await updateAnnotations([
            {
                annotation_id: annotation.id,
                collection_id: annotation.annotationSourceId,
                ...(isNewTrack ? { create_new_track: true } : { object_track_id: trackId })
            }
        ]);
        await tracksQuery.refetch();
        onTrackChange?.();
    }
</script>

<dl class="space-y-3 text-diffuse-foreground" data-testid="point-cloud-annotation-details">
    <AnnotationGeometryGroup
        title="Location:"
        group="location"
        fields={['x', 'y', 'z']}
        labels={['X', 'Y', 'Z']}
        displayValues={details.location}
        step={0.01}
        {editable}
        {editing}
    />
    <AnnotationGeometryGroup
        title="Dimensions (m):"
        group="dimension"
        fields={['l', 'w', 'h']}
        labels={['L', 'W', 'H']}
        displayValues={details.dimensions}
        step={0.01}
        min={0.01}
        {editable}
        {editing}
    />
    <AnnotationGeometryGroup
        title="Rotation:"
        group="rotation"
        fields={['rx', 'ry', 'rz']}
        labels={['rx', 'ry', 'rz']}
        displayValues={details.rotation}
        step={0.1}
        suffix="°"
        {editable}
        {editing}
    />

    {#if details.annotationSourceName}
        <div class="grid grid-cols-[5rem_1fr] gap-x-2">
            <Typography component="dt" variant="body2">Annotation source:</Typography>
            <Typography component="dd" variant="body2">{details.annotationSourceName}</Typography>
        </div>
    {/if}

    {#if editable}
        <div class="grid grid-cols-[5rem_1fr] gap-x-2">
            <Typography component="dt" variant="body2">Track:</Typography>
            <dd>
                <TrackSelect
                    {tracks}
                    value={annotation.trackId ?? '__no_track__'}
                    onValueChange={handleTrackChange}
                />
            </dd>
        </div>
    {:else if details.trackNumber !== null}
        <div class="grid grid-cols-[5rem_1fr] gap-x-2">
            <Typography component="dt" variant="body2">Track number:</Typography>
            <Typography component="dd" variant="body2">{details.trackNumber}</Typography>
        </div>
    {/if}
</dl>
