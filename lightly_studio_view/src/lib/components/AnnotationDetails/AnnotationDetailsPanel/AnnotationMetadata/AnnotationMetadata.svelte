<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { isClassificationAnnotation } from '$lib/services/types';
    import { formatInteger } from '$lib/utils';
    import { getBoundingBox } from '$lib/components/SampleAnnotation/utils';
    import { ANNOTATION_TYPES } from '$lib/constants';
    import { page } from '$app/state';
    import AnnotationMetadataItem from './AnnotationMetadataItem/AnnotationMetadataItem.svelte';
    import AnnotationMetadataLabel from './AnnotationMetadataLabel/AnnotationMetadataLabel.svelte';
    import { useAnnotation } from '$lib/hooks/useAnnotation/useAnnotation';

    const {
        annotationId,
        onUpdate
    }: {
        annotationId: string;
        onUpdate?: () => void;
    } = $props();

    const { datasetId } = page.data;

    const { annotation: annotationResp } = $derived(
        useAnnotation({
            datasetId,
            annotationId
        })
    );

    let annotation = $derived($annotationResp.data);

    const annotationMetadata = $derived.by(() => {
        if (!annotation) {
            return [];
        }
        let annotationsMetadata = [
            {
                id: 'label',
                label: 'Label:',
                value: annotation?.annotation_label?.annotation_label_name
            },
            {
                id: 'type',
                label: 'Type:',
                value:
                    ANNOTATION_TYPES[annotation.annotation_type as keyof typeof ANNOTATION_TYPES] ||
                    'Unknown'
            }
        ];

        if (annotation && !isClassificationAnnotation(annotation)) {
            const { height, width } = getBoundingBox(annotation);
            annotationsMetadata = [
                {
                    id: 'height',
                    label: 'Height:',
                    value: formatInteger(Math.round(height)) + 'px'
                },
                {
                    id: 'width',
                    label: 'Width:',
                    value: formatInteger(Math.round(width)) + 'px'
                },
                ...annotationsMetadata
            ];
        }

        return annotationsMetadata;
    });
    const { isEditingMode } = page.data.globalStorage;
</script>

{#if annotationMetadata.length > 0}
    <Segment title="Annotation details">
        <div class="flex flex-col gap-4">
            <div class="grid grid-cols-[6rem_1fr] gap-y-3 text-diffuse-foreground">
                {#each annotationMetadata as { label, value, id } (label)}
                    {#if id === 'label' && isEditingMode}
                        <AnnotationMetadataLabel
                            {onUpdate}
                            {annotationId}
                            {datasetId}
                            {label}
                            {value}
                            {isEditingMode}
                        />
                    {:else}
                        <AnnotationMetadataItem {label} {id} {value} />
                    {/if}
                {/each}
            </div>
        </div>
    </Segment>
{/if}
