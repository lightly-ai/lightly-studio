<script lang="ts">
    import { createAnnotationDetails } from './pointCloudAnnotationDetails';
    import { useAnnotationDetailsEditing } from './useAnnotationDetailsEditing.svelte';
    import AnnotationGeometryGroup from './AnnotationGeometryGroup';
    import { Typography } from '$lib/components/Typography';

    type AnnotationInput = Parameters<typeof createAnnotationDetails>[0]['annotation'];

    interface Props {
        /** Cuboid whose metadata is displayed. */
        annotation: AnnotationInput;
        /** Human-readable annotation source name, when available. */
        annotationSourceName?: string;
        /** When true, numeric fields become editable inputs. */
        editable?: boolean;
        /** Called with the full updated annotation when a field is committed. */
        onAnnotationChange?: (annotation: AnnotationInput) => void;
    }

    let {
        annotation,
        annotationSourceName,
        editable = false,
        onAnnotationChange
    }: Props = $props();
    const details = $derived(createAnnotationDetails({ annotation, annotationSourceName }));
    const editing = useAnnotationDetailsEditing(
        () => annotation,
        (updated) => onAnnotationChange?.(updated)
    );
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

    {#if details.trackNumber !== null}
        <div class="grid grid-cols-[5rem_1fr] gap-x-2">
            <Typography component="dt" variant="body2">Track number:</Typography>
            <Typography component="dd" variant="body2">{details.trackNumber}</Typography>
        </div>
    {/if}
</dl>
