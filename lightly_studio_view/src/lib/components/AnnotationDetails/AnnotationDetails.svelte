<script lang="ts">
    import { routeHelpers } from '$lib/routes';
    import AnnotationDetailsPanel from './AnnotationDetailsPanel/AnnotationDetailsPanel.svelte';
    import AnnotationDetailsBreadcrumb from './AnnotationDetailsBreadcrumb/AnnotationDetailsBreadcrumb.svelte';

    import {
        type AnnotationDetailsWithPayloadView,
        type AnnotationUpdateInput,
        type AnnotationView
    } from '$lib/api/lightly_studio_local';
    import type { Snippet } from 'svelte';
    import SampleDetailsPanel from '../SampleDetails/SampleDetailsPanel.svelte';
    import { goto } from '$app/navigation';
    import AnnotationDetailsNavigation from './AnnotationDetailsNavigation/AnnotationDetailsNavigation.svelte';
    import AnnotationDetailsSelectableBox from './AnnotationDetailsSelectableBox/AnnotationDetailsSelectableBox.svelte';

    type SampleProperties = {
        width: number;
        height: number;
        url: string;
    };

    const {
        annotationIndex,
        annotationDetails,
        parentSample,
        parentSampleDetails,
        refetch,
        collectionId
    }: {
        annotationIndex?: number;
        annotationDetails: AnnotationDetailsWithPayloadView;
        parentSample: SampleProperties;
        parentSampleDetails: Snippet;
        updateAnnotation: (input: AnnotationUpdateInput) => Promise<void>;
        refetch: () => void;
        collectionId: string;
    } = $props();
    const handleEscape = () => {
        if (annotationDetails.parent_sample_data?.sample.collection_id) {
            goto(
                routeHelpers.toAnnotations(
                    annotationDetails.parent_sample_data.sample.collection_id
                )
            );
        } else {
            goto('/');
        }
    };

    let annotation: AnnotationView = $derived(annotationDetails.annotation);
</script>

<SampleDetailsPanel
    {collectionId}
    sampleId={annotation.sample_id}
    sampleURL={parentSample.url}
    sampleType={'annotation'}
    sample={{
        sample_id: annotation.parent_sample_id,
        width: parentSample.width,
        height: parentSample.height,
        annotations: [annotation],
        tags: [],
        captions: []
    }}
    {refetch}
    {handleEscape}
>
    {#snippet children()}
        <AnnotationDetailsNavigation />
    {/snippet}
    {#snippet breadcrumb({ collection: rootCollection })}
        <AnnotationDetailsBreadcrumb {rootCollection} {annotationIndex} />
    {/snippet}
    {#snippet selectableBox()}
        <AnnotationDetailsSelectableBox {collectionId} sampleId={annotation.sample_id} />
    {/snippet}
    {#snippet sidePanelItem()}
        <AnnotationDetailsPanel {annotation} onUpdate={refetch} {collectionId}>
            {#snippet sampleDetails()}
                {@render parentSampleDetails()}
            {/snippet}
        </AnnotationDetailsPanel>
    {/snippet}
</SampleDetailsPanel>
