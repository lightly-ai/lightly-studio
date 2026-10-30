<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';
    import { createCuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import PointCloudAnnotationList from './PointCloudAnnotationList.svelte';

    const base = createAnnotationFixture();

    const classes = [
        { id: 'vehicle', name: 'Vehicle', color: '#3b82f6' },
        { id: 'pedestrian', name: 'Pedestrian', color: '#22d3ee' },
        { id: 'truck', name: 'Truck', color: '#f59e0b' },
        { id: 'cabin', name: 'Cabin', color: '#10b981' },
        { id: 'trailer', name: 'Trailer', color: '#8b5cf6' },
        { id: 'window', name: 'Window', color: '#ef4444' }
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

    // Single-level parent group: Truck #1 → Cabin #2, Trailer #3
    const truck = createCuboidAnnotation({
        ...base,
        id: 'truck',
        annotationClassId: 'truck',
        annotationSourceId: 'ground-truth',
        trackNumber: 1,
        parentTrackNumber: null
    });
    const cabin = createCuboidAnnotation({
        ...base,
        id: 'cabin',
        annotationClassId: 'cabin',
        annotationSourceId: 'ground-truth',
        trackNumber: 2,
        parentTrackNumber: 1
    });
    const trailer = createCuboidAnnotation({
        ...base,
        id: 'trailer',
        annotationClassId: 'trailer',
        annotationSourceId: 'ground-truth',
        trackNumber: 3,
        parentTrackNumber: 1
    });

    // Multi-level group: Truck #1 → Cabin #2 → Window #3
    const truckMulti = createCuboidAnnotation({
        ...base,
        id: 'truck-multi',
        annotationClassId: 'truck',
        annotationSourceId: 'ground-truth',
        trackNumber: 1,
        parentTrackNumber: null
    });
    const cabinMulti = createCuboidAnnotation({
        ...base,
        id: 'cabin-multi',
        annotationClassId: 'cabin',
        annotationSourceId: 'ground-truth',
        trackNumber: 2,
        parentTrackNumber: 1
    });
    const windowMulti = createCuboidAnnotation({
        ...base,
        id: 'window-multi',
        annotationClassId: 'window',
        annotationSourceId: 'ground-truth',
        trackNumber: 3,
        parentTrackNumber: 2
    });

    // Orphaned child: parent track number 99 does not exist
    const orphan = createCuboidAnnotation({
        ...base,
        id: 'orphan',
        annotationClassId: 'pedestrian',
        annotationSourceId: 'ground-truth',
        trackNumber: 5,
        parentTrackNumber: 99
    });

    // Absent parent group: children reference a parent not in frame, but have className
    const absentChild1 = createCuboidAnnotation({
        ...base,
        id: 'absent-cabin',
        annotationClassId: 'cabin',
        annotationSourceId: 'ground-truth',
        trackNumber: 10,
        parentTrackNumber: 99,
        parentTrackClassName: 'truck'
    });
    const absentChild2 = createCuboidAnnotation({
        ...base,
        id: 'absent-trailer',
        annotationClassId: 'trailer',
        annotationSourceId: 'ground-truth',
        trackNumber: 11,
        parentTrackNumber: 99,
        parentTrackClassName: 'truck'
    });

    // Root with null trackNumber and children
    const nullTrackRoot = createCuboidAnnotation({
        ...base,
        id: 'null-track-root',
        annotationClassId: 'truck',
        annotationSourceId: 'ground-truth',
        trackNumber: null,
        parentTrackNumber: null
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

<Story
    name="Parent group — single level"
    args={{
        cuboids: [truck, cabin, trailer],
        annotationSources: [sources[0]]
    }}
/>

<Story
    name="Parent group — multi level"
    args={{
        cuboids: [truckMulti, cabinMulti, windowMulti],
        annotationSources: [sources[0]]
    }}
/>

<Story
    name="Flat root — no children"
    args={{
        cuboids: [gtCuboid1],
        annotationSources: [sources[0]]
    }}
/>

<Story
    name="Orphaned child"
    args={{
        cuboids: [orphan],
        annotationSources: [sources[0]]
    }}
/>

<Story
    name="Root with null track number"
    args={{
        cuboids: [nullTrackRoot],
        annotationSources: [sources[0]]
    }}
/>

<Story
    name="Absent parent group"
    args={{
        cuboids: [absentChild1, absentChild2],
        annotationSources: [sources[0]]
    }}
/>
