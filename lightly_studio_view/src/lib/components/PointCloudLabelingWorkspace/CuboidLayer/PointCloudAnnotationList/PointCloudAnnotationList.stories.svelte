<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';
    import { createCuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import PointCloudAnnotationList from './PointCloudAnnotationList.svelte';

    const base = createAnnotationFixture();

    const classes = [
        { id: 'vehicle', name: 'Vehicle', color: '#3b82f6' },
        { id: 'pedestrian', name: 'Pedestrian', color: '#22d3ee' }
    ];

    const sources = [
        { id: 'ground-truth', name: 'Ground Truth' },
        { id: 'predictions', name: 'Predictions' }
    ];

    const gtCuboid1 = createCuboidAnnotation({
        ...base,
        id: 'annotation-0',
        annotationClassId: 'vehicle',
        annotationSourceId: 'ground-truth'
    });
    const gtCuboid2 = createCuboidAnnotation({
        ...base,
        id: 'annotation-1',
        annotationClassId: 'pedestrian',
        annotationSourceId: 'ground-truth'
    });
    const predCuboid = createCuboidAnnotation({
        ...base,
        id: 'annotation-2',
        annotationClassId: 'vehicle',
        annotationSourceId: 'predictions'
    });

    const { Story } = defineMeta({
        title: 'Components/PointCloudLabelingWorkspace/PointCloudAnnotationList',
        component: PointCloudAnnotationList,
        tags: ['autodocs'],
        parameters: { layout: 'padded' },
        args: {
            cuboids: [gtCuboid1, gtCuboid2],
            annotationClasses: classes,
            annotationSources: [sources[0]],
            selectedCuboidId: null
        }
    });
</script>

<Story name="Empty" args={{ cuboids: [], annotationSources: sources }} />

<Story name="Single source" />

<Story name="Single source — expanded" args={{ selectedCuboidId: 'annotation-0' }} />

<Story
    name="Multiple sources"
    args={{
        cuboids: [gtCuboid1, gtCuboid2, predCuboid],
        annotationSources: sources,
        selectedCuboidId: 'annotation-2'
    }}
/>
